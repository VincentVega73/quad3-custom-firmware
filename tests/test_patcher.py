"""Patcher failure, file-preservation, and synthetic layout tests; no vendor image."""

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch as replace
import uuid

import firmware_patch as firmware
import qualify_rc2 as qualification


def synthetic_original() -> bytes:
    """Locally generated filler, not extracted firmware or executable test code."""
    data = bytearray([0xA5]) * firmware.ORIGINAL_SIZE
    data[firmware.HOOK:firmware.HOOK + 4] = firmware.ORIGINAL_HOOK
    start = firmware.COMMAND_TABLE_OFFSET
    data[start:start + len(firmware.EXPECTED_COMMAND_PAIRS)] = firmware.EXPECTED_COMMAND_PAIRS
    return bytes(data)


class PatcherTests(unittest.TestCase):
    def setUp(self):
        # Ordinary mkdir avoids platform-specific restrictive tempfile ACLs.
        self.parent = (firmware.HERE / "generated").resolve()
        self.directory = self.parent / ("unit-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True)
        self.original = synthetic_original()
        self.source = self.directory / "synthetic-input.fixture"
        self.source.write_bytes(self.original)
        self.output = self.directory / "candidate.fixture"
        self.manifest = self.directory / "manifest.json"
        self.expected = bytearray(self.original)
        self.expected[firmware.HOOK:firmware.HOOK + 4] = firmware.BRANCH
        self.expected.extend(firmware.PAYLOAD)
        self.expected = bytes(self.expected)

    def tearDown(self):
        resolved = self.directory.resolve()
        if resolved.parent != self.parent or not resolved.name.startswith("unit-"):
            raise RuntimeError("Refusing cleanup outside this test's generated directory")
        shutil.rmtree(resolved)

    def synthetic_hashes(self):
        """Tests alone substitute synthetic hashes; production has no bypass flag."""
        stack = ExitStack()
        stack.enter_context(replace.object(firmware, "ORIGINAL_SHA256", firmware.sha256(self.original)))
        stack.enter_context(replace.object(firmware, "EXPECTED_RC2", firmware.sha256(self.expected)))
        return stack

    def call_builder(self, *extra):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            return firmware.main([
                "--input", str(self.source), "--output", str(self.output),
                "--manifest", str(self.manifest), *extra,
            ])

    def test_wrong_length_hook_table_and_hash_are_rejected(self):
        examples = []
        examples.append((self.original[:-1], "size"))
        changed = bytearray(self.original)
        changed[firmware.HOOK] ^= 1
        examples.append((bytes(changed), "hook"))
        changed = bytearray(self.original)
        changed[firmware.COMMAND_TABLE_OFFSET] ^= 1
        examples.append((bytes(changed), "table"))
        examples.append((self.original, "SHA256"))
        for data, diagnostic in examples:
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(ValueError, diagnostic):
                firmware.validate_original(data)

    def test_invalid_input_writes_nothing(self):
        self.assertEqual(self.call_builder(), 2)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_python_optimized_mode_keeps_binary_guards(self):
        for script in ("firmware_patch.py", "qualify_rc2.py"):
            command = [sys.executable, "-O", str(firmware.HERE / script), "--input", str(self.source)]
            if script == "firmware_patch.py":
                command.extend(["--output", str(self.output), "--manifest", str(self.manifest)])
            else:
                command.extend(["--candidate", str(self.output)])
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA256 mismatch" if script == "firmware_patch.py" else "ERROR:", result.stderr)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())

    def test_source_output_and_manifest_aliases_are_rejected(self):
        pairs = ((self.source, self.manifest), (self.output, self.source), (self.output, self.output))
        for output, manifest in pairs:
            with self.subTest(output=output, manifest=manifest), self.assertRaises(ValueError):
                firmware.validate_output_paths(self.source, output, manifest)
        alias = self.directory / "hardlink.fixture"
        os.link(self.source, alias)
        with self.assertRaisesRegex(ValueError, "original"):
            firmware.validate_output_paths(self.source, alias, self.manifest)
        with self.assertRaisesRegex(ValueError, "original"):
            firmware.validate_output_paths(self.source, self.output, alias)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_synthetic_generation_is_deterministic_and_preserves_input(self):
        with self.synthetic_hashes():
            self.assertEqual(self.call_builder(), 0)
            first_manifest = self.manifest.read_bytes()
            self.assertEqual(self.call_builder(), 0)
        self.assertEqual(self.output.read_bytes(), self.expected)
        self.assertEqual(self.manifest.read_bytes(), first_manifest)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_different_existing_destination_prevents_both_writes(self):
        for existing in (self.output, self.manifest):
            with self.subTest(existing=existing):
                existing.write_bytes(b"do not replace")
                with self.synthetic_hashes():
                    self.assertEqual(self.call_builder(), 2)
                self.assertEqual(existing.read_bytes(), b"do not replace")
                other = self.manifest if existing == self.output else self.output
                self.assertFalse(other.exists())
                existing.unlink()
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_missing_mapping_blocks_before_writing(self):
        mapping = firmware.load_mapping()
        row = mapping["buttons"][3]
        row["physical_mapping_status"] = "unverified"
        for field in firmware.CODE_FIELDS:
            row[field] = None
        with self.synthetic_hashes(), replace.object(firmware, "load_mapping", return_value=mapping):
            self.assertEqual(self.call_builder(), 3)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())

    def test_changed_payload_and_flash_overflow_are_rejected(self):
        altered = bytes([firmware.PAYLOAD[0] ^ 1]) + firmware.PAYLOAD[1:]
        with self.synthetic_hashes(), replace.object(firmware, "PAYLOAD", altered):
            with self.assertRaisesRegex(ValueError, "SHA256"):
                firmware.build(self.original)
        with self.synthetic_hashes(), replace.object(firmware, "FLASH_LIMIT_EXCLUSIVE", firmware.BASE + firmware.RC2_SIZE - 1):
            with self.assertRaisesRegex(ValueError, "boundary"):
                firmware.build(self.original)

    def test_manifest_refuses_a_different_candidate(self):
        with self.synthetic_hashes(), self.assertRaisesRegex(ValueError, "differs"):
            firmware.get_manifest(self.original, self.expected[:-1] + b"X")

    def test_synthetic_qualification_and_corruption(self):
        with self.synthetic_hashes():
            result = qualification.qualify(self.original, self.expected)
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["physical_rc2_tested"])
            with self.assertRaisesRegex(ValueError, "size"):
                qualification.qualify(self.original, self.expected[:-1])
            changed = self.expected[:100] + b"X" + self.expected[101:]
            with self.assertRaisesRegex(ValueError, "SHA256"):
                qualification.qualify(self.original, changed)
            with replace.object(firmware, "EXPECTED_RC2", firmware.sha256(changed)):
                with self.assertRaisesRegex(ValueError, "Vector table"):
                    qualification.qualify(self.original, changed)

    def test_qualification_report_cannot_alias_firmware(self):
        self.output.write_bytes(self.expected)
        for report in (self.source, self.output):
            with self.synthetic_hashes(), redirect_stderr(StringIO()):
                result = qualification.main([
                    "--input", str(self.source), "--candidate", str(self.output), "--report", str(report),
                ])
            self.assertEqual(result, 2)
        alias = self.directory / "report-hardlink.fixture"
        os.link(self.source, alias)
        with redirect_stderr(StringIO()):
            result = qualification.main([
                "--input", str(self.source), "--candidate", str(self.output), "--report", str(alias),
            ])
        self.assertEqual(result, 2)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(self.output.read_bytes(), self.expected)


class BranchTests(unittest.TestCase):
    def test_forward_hook_and_negative_native_branches(self):
        self.assertEqual(qualification.decode_wide_branch(firmware.BRANCH, 0x08013346), 0x0801D8F8)
        self.assertEqual(qualification.decode_wide_branch(firmware.PAYLOAD[72:76], 0x0801D940), 0x0801334A)
        self.assertEqual(qualification.decode_wide_branch(firmware.PAYLOAD[108:112], 0x0801D964), 0x080131F8)
        self.assertEqual(qualification.decode_wide_branch(firmware.PAYLOAD[116:120], 0x0801D96C), 0x080134D4)

    def test_bad_instructions_and_alignment(self):
        for data, address in ((b"xx", 0x08013346), (b"\x00" * 4, 0x08013346), (firmware.BRANCH, 0x08013347)):
            with self.subTest(data=data, address=address), self.assertRaises(ValueError):
                qualification.decode_wide_branch(data, address)


if __name__ == "__main__":
    unittest.main()
