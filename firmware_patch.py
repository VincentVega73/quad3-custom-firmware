"""Reproducibly build SK2-RC2 from the exact user-supplied QUAD 3 v1.14j image.

Standard library only. No hardware access. The input is read only; generated
vendor-derived images must remain local and must not be committed or uploaded.
SK2-RC2 is a release candidate, not a physically validated firmware release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
APPLICATION_BASE = 0x08010000
ORIGINAL_SIZE = 0xD8F8
ORIGINAL_SHA256 = "7dff59e986643543c28c7f71c1f43f78c936867b25b078e0c1bd0ea5a6fe3853"
HOOK_OFFSET = 0x3346
ORIGINAL_HOOK = bytes.fromhex("2088c01f")
FLASH_LIMIT_EXCLUSIVE = 0x08020000
VECTOR_TABLE_SIZE = 0x120
OUTPUT_NAME = "QUAD3_v1.14j-SK2-RC2.bin"
MANIFEST_NAME = "patch_manifest_sk2_rc2.json"
TARGET_SOURCES = (1, 5, 6, 7, 3, 2, 4, 0, None, None)
KNOWN_EVENTS = {"0": 0x5017, "1": 0x5018, "2": 0x5019}
EXPECTED_EVENTS = (0x5017, 0x5018, 0x5019, 0x501A, 0x501B, 0x501C, 0x501D, 0x501E)
EXPECTED_COMMANDS = (0x33, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29)
COMMAND_TABLE_OFFSET = 0xCB82
EXPECTED_COMMAND_PAIRS = bytes.fromhex("cc17c4182419a41a641be41c141d941e")
BRANCH = bytes.fromhex("0af0d7ba")
PAYLOAD = bytes.fromhex(
    "208806b445f2170188421fd045f2180188421dd045f2190188421bd045f21a01884219d0"
    "45f21b01884217d045f21c01884215d045f21d01884213d045f21e01884211d006bcc01f"
    "f5f703bd01250ce005250ae0062508e0072506e0032504e0022502e0042500e0002506bc"
    "f5f748fc01490d70f5f7b2bdd30e0020"
)
EXPECTED_RC2 = "08555b7437781bcef803f6469eb56428aa1dc30716a262938f7b211a0e863146"
RC2_SIZE = 55668
HANDLER_CODE_SIZE = 120
# Names shared with the existing local instruction-execution harness.
BASE = APPLICATION_BASE
EXPECTED = ORIGINAL_SHA256
HOOK = HOOK_OFFSET
MIN_COMPATIBLE_FLASH_LIMIT = FLASH_LIMIT_EXCLUSIVE
NAME = OUTPUT_NAME
CODE_FIELDS = (
    "event", "internal_id", "nec_address_bytes", "nec_command",
    "nec_inverse_command", "decoder_address", "decoder_command",
)


class ReleaseBlockedError(RuntimeError):
    """Evidence or an approved RC2 patch definition is absent."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_original(data: bytes) -> None:
    """Require the exact unmodified baseline, with checks active under python -O."""
    if len(data) != ORIGINAL_SIZE:
        raise ValueError(f"Original size mismatch: {len(data)}; expected {ORIGINAL_SIZE}")
    if data[HOOK_OFFSET:HOOK_OFFSET + 4] != ORIGINAL_HOOK:
        raise ValueError("Original hook bytes mismatch at file offset 0x3346")
    if data[COMMAND_TABLE_OFFSET:COMMAND_TABLE_OFFSET + len(EXPECTED_COMMAND_PAIRS)] != EXPECTED_COMMAND_PAIRS:
        raise ValueError("Original IR decoder table pairs mismatch at file offset 0xCB82")
    if sha256(data) != ORIGINAL_SHA256:
        raise ValueError("Original SHA256 mismatch; only the pinned v1.14j image is accepted")


def _integer(value: Any, field: str, maximum: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer or a hexadecimal string")
    try:
        result = int(value, 16) if isinstance(value, str) and value.startswith("0x") else value
    except ValueError as exc:
        raise ValueError(f"Invalid {field}") from exc
    if not isinstance(result, int) or not 0 <= result <= maximum:
        raise ValueError(f"{field} must be within 0..{maximum}")
    return result


def _reverse_byte(value: int) -> int:
    return int(f"{value:08b}"[::-1], 2)


def validate_mapping(mapping: dict[str, Any]) -> list[str]:
    """Validate published evidence; return active buttons still awaiting mapping.

    This is a consistency check, not an independent authentication of captures.
    The reviewed machine code and expected binary SHA256 are separately pinned.
    """
    if type(mapping.get("schema_version")) is not int or mapping["schema_version"] != 1:
        raise ValueError("Unsupported IR mapping schema_version")
    release = mapping.get("release")
    if not isinstance(release, dict) or release.get("name") != "SK2-RC2":
        raise ValueError("IR mapping must identify release SK2-RC2")
    buttons = mapping.get("buttons")
    if not isinstance(buttons, list) or len(buttons) != 10:
        raise ValueError("IR mapping must contain exactly buttons 0 through 9")
    indexed: dict[str, dict[str, Any]] = {}
    for row in buttons:
        if not isinstance(row, dict):
            raise ValueError("Each IR button entry must be an object")
        label = row.get("button")
        if not isinstance(label, str) or label not in tuple(str(i) for i in range(10)):
            raise ValueError("Button labels must be strings 0 through 9")
        if label in indexed:
            raise ValueError(f"Duplicate physical button {label}")
        indexed[label] = row
    missing: list[str] = []
    seen_events: set[int] = set()
    for number, expected_source in enumerate(TARGET_SOURCES):
        label = str(number)
        row = indexed[label]
        source = row.get("source_id")
        if source != expected_source or (source is not None and type(source) is not int):
            raise ValueError(f"Button {label} has the wrong SK2 source ID")
        status = row.get("physical_mapping_status")
        if number >= 8:
            if status != "reserved" or any(row.get(field) is not None for field in CODE_FIELDS):
                raise ValueError(f"Button {label} must remain reserved without an assigned event")
            continue
        if status not in {"owner_observed", "physical_capture_confirmed", "unverified"}:
            raise ValueError(f"Button {label} has an unsupported physical evidence status")
        if status == "unverified":
            if any(row.get(field) is not None for field in CODE_FIELDS):
                raise ValueError(f"Unverified physical button {label} must not be assigned guessed codes")
            if label in KNOWN_EVENTS:
                raise ValueError(f"Existing owner evidence for button {label} must be preserved")
            missing.append(label)
            continue
        if row.get("firmware_status") != "confirmed" or not row.get("provenance"):
            raise ValueError(f"Button {label} requires firmware confirmation and provenance")
        event = _integer(row.get("event"), f"button {label} event", 0xFFFF)
        internal_id = _integer(row.get("internal_id"), f"button {label} internal_id", 0xFF)
        if event != 0x5000 + internal_id:
            raise ValueError(f"Button {label} is not the corresponding short-release event")
        if label in KNOWN_EVENTS and event != KNOWN_EVENTS[label]:
            raise ValueError(f"Button {label} conflicts with the verified SK1 physical mapping")
        if event != EXPECTED_EVENTS[number]:
            raise ValueError(f"Button {label} conflicts with the reviewed decoder table mapping")
        if event in seen_events:
            raise ValueError("Two physical buttons share a direct-source event")
        seen_events.add(event)
        address = row.get("nec_address_bytes")
        if not isinstance(address, list) or len(address) != 2:
            raise ValueError(f"Button {label} requires two NEC address bytes")
        a0, a1 = (_integer(value, f"button {label} address byte", 0xFF) for value in address)
        raw_address = _integer(row.get("decoder_address"), f"button {label} decoder_address", 0xFFFF)
        if (a0, a1) != (0x32, 0xEE) or raw_address != 0x4C77:
            raise ValueError(f"Button {label} is outside the confirmed amplifier address")
        if raw_address != (_reverse_byte(a0) << 8) | _reverse_byte(a1):
            raise ValueError(f"Button {label} decoder address bit order is inconsistent")
        command = _integer(row.get("nec_command"), f"button {label} nec_command", 0xFF)
        inverse = _integer(row.get("nec_inverse_command"), f"button {label} inverse", 0xFF)
        raw_command = _integer(row.get("decoder_command"), f"button {label} decoder_command", 0xFF)
        if command ^ inverse != 0xFF:
            raise ValueError(f"Button {label} NEC command and inverse are inconsistent")
        if raw_command != _reverse_byte(command):
            raise ValueError(f"Button {label} decoder command bit order is inconsistent")
        if command != EXPECTED_COMMANDS[number]:
            raise ValueError(f"Button {label} conflicts with the owner-reported physical capture")
    return missing


def load_mapping(path: Path = HERE / "data" / "ir_mapping.json") -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("IR mapping root must be an object")
    return value


def require_approved_release(mapping: dict[str, Any]) -> None:
    missing = validate_mapping(mapping)
    if missing:
        raise ReleaseBlockedError(
            "SK2-RC2 requires physical IR captures for amplifier-mode buttons "
            + ", ".join(missing)
            + ". See docs/IR_CODES.md. No RC2 binary or manifest was written."
        )
    if mapping["release"].get("status") != "release_candidate":
        raise ReleaseBlockedError("IR mapping release status must be release_candidate")


def build(data: bytes) -> tuple[bytes, bytes, bytes]:
    """Apply the frozen patch after checking every pinned binary precondition."""
    validate_original(data)
    if len(BRANCH) != 4 or len(PAYLOAD) != 124 or HANDLER_CODE_SIZE != 120:
        raise ValueError("Patch definition length mismatch")
    result = data[:HOOK_OFFSET] + BRANCH + data[HOOK_OFFSET + 4:] + PAYLOAD
    if result[:HOOK_OFFSET] != data[:HOOK_OFFSET] or result[HOOK_OFFSET + 4:ORIGINAL_SIZE] != data[HOOK_OFFSET + 4:]:
        raise ValueError("Unexpected modification outside the dispatcher hook")
    if len(result) != RC2_SIZE or APPLICATION_BASE + len(result) > FLASH_LIMIT_EXCLUSIVE:
        raise ValueError("RC2 image length or minimum compatible flash boundary mismatch")
    if sha256(result) != EXPECTED_RC2:
        raise ValueError("RC2 SHA256 mismatch: patch definition differs from the frozen release candidate")
    return result, PAYLOAD, BRANCH


def get_manifest(original: bytes, result: bytes) -> dict[str, Any]:
    expected, _, _ = build(original)
    if result != expected:
        raise ValueError("Cannot describe a candidate that differs from the frozen patch")
    return {
        "schema_version": 1,
        "release": "SK2-RC2",
        "status": "release_candidate",
        "original_sha256": sha256(original),
        "patched_sha256": sha256(result),
        "original_size": len(original),
        "patched_size": len(result),
        "application_base": hex(APPLICATION_BASE),
        "original_end_exclusive": hex(APPLICATION_BASE + len(original)),
        "patched_end_exclusive": hex(APPLICATION_BASE + len(result)),
        "patched_last_byte": hex(APPLICATION_BASE + len(result) - 1),
        "handler_code_size": HANDLER_CODE_SIZE,
        "handler_size": len(PAYLOAD),
        "handler_literal_address": hex(APPLICATION_BASE + ORIGINAL_SIZE + HANDLER_CODE_SIZE),
        "minimum_compatible_flash_limit_exclusive": hex(FLASH_LIMIT_EXCLUSIVE),
        "remaining_bytes_under_minimum_compatible_model": FLASH_LIMIT_EXCLUSIVE - APPLICATION_BASE - len(result),
        "actual_mcu_identification": "Not physically read; STM32F100xB minimum compatible model inferred",
        "changes": [
            {"offset": hex(HOOK_OFFSET), "end_exclusive": hex(HOOK_OFFSET + 4),
             "original_hex": ORIGINAL_HOOK.hex(), "patched_hex": BRANCH.hex(),
             "purpose": "Thumb B.W to appended handler"},
            {"offset": hex(ORIGINAL_SIZE), "end_exclusive": hex(len(result)),
             "original_hex": "", "patched_hex": PAYLOAD.hex(),
             "purpose": "Eight direct selections through the native source path"},
        ],
        "commands": [
            {"button": str(i), "event": hex(EXPECTED_EVENTS[i]), "source_id": TARGET_SOURCES[i],
             "nec_command": hex(EXPECTED_COMMANDS[i])} for i in range(8)
        ],
        "physical_mapping_evidence": "Owner-reported AMP-mode VS1838B/ESP32 captures; see data/ir_mapping.json",
        "qualification": "Generation verifies deterministic bytes only; run qualify_rc2.py and local emulator suites",
        "physical_rc2_tested": False,
        "system_version_string_changed": False,
        "nvram_format_changed": False,
        "known_checksum_updated": False,
        "known_signature_updated": False,
        "scope": "Short release events only, with original power/protection guards and native source worker",
    }


def _same_path(first: Path, second: Path) -> bool:
    if first.resolve() == second.resolve():
        return True
    return first.exists() and second.exists() and first.samefile(second)


def validate_output_paths(source: Path, output: Path, manifest: Path) -> None:
    if _same_path(source, output) or _same_path(source, manifest):
        raise ValueError("Never overwrite the original input, including through an alias")
    if _same_path(output, manifest):
        raise ValueError("Firmware and manifest require different output paths")


def write_new_or_identical(path: Path, data: bytes) -> None:
    """Never replace an existing, different file or truncate a racing new file."""
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f"Refusing to replace a different file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
    if path.read_bytes() != data:
        raise OSError(f"Written bytes differ from expected content: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Legally obtained stock image; read only")
    parser.add_argument("--output", type=Path, default=HERE / "generated" / OUTPUT_NAME,
                        help="Local output image; never commit or upload it")
    parser.add_argument("--manifest", type=Path, default=HERE / "generated" / MANIFEST_NAME,
                        help="Deterministic patch manifest")
    args = parser.parse_args(argv)
    try:
        validate_output_paths(args.input, args.output, args.manifest)
        original = args.input.read_bytes()
        validate_original(original)
        print(f"Original verified: {len(original)} bytes; SHA256 {sha256(original)}")
        require_approved_release(load_mapping())
        result, _, _ = build(original)
        manifest = get_manifest(original, result)
        manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
        # Validate both destinations before writing either deliverable.
        for path, expected in ((args.output, result), (args.manifest, manifest_bytes)):
            if path.exists() and path.read_bytes() != expected:
                raise FileExistsError(f"Refusing to replace a different file: {path}")
        write_new_or_identical(args.output, result)
        write_new_or_identical(args.manifest, manifest_bytes)
        if args.input.read_bytes() != original:
            raise OSError("Input changed during generation; generated files are not qualified")
        print(json.dumps(manifest, indent=2))
        return 0
    except ReleaseBlockedError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 3
    except (OSError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
