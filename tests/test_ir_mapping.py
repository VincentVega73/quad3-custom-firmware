"""Validate captured-code evidence and reserved buttons without vendor firmware."""

from copy import deepcopy
import json
import unittest

import firmware_patch as firmware


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.mapping = firmware.load_mapping()

    def test_all_eight_captures_are_present(self):
        self.assertEqual(firmware.validate_mapping(self.mapping), [])
        firmware.require_approved_release(self.mapping)
        for row in self.mapping["buttons"][:8]:
            self.assertEqual(row["physical_mapping_status"], "physical_capture_confirmed")
            self.assertTrue(row["provenance"])

    def test_source_enum_matches_final_layout(self):
        data = json.loads((firmware.HERE / "data" / "source_enum.json").read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual({row["id"]: row["name"] for row in data["sources"]}, {
            0: "Bluetooth", 1: "USB", 2: "Optical", 3: "Coax",
            4: "ARC", 5: "AUX1", 6: "AUX2", 7: "Phono",
        })
        self.assertEqual(tuple(row["source_id"] for row in self.mapping["buttons"]), firmware.TARGET_SOURCES)
        self.assertEqual(self.mapping["buttons"][2]["source_id"], 6)
        self.assertEqual(self.mapping["buttons"][6]["source_id"], 4)

    def test_duplicate_and_missing_labels_fail(self):
        for rows in (self.mapping["buttons"][:-1], self.mapping["buttons"][:-1] + [self.mapping["buttons"][0]]):
            changed = deepcopy(self.mapping)
            changed["buttons"] = rows
            with self.assertRaises(ValueError):
                firmware.validate_mapping(changed)

    def test_reserved_buttons_cannot_gain_a_source_or_event(self):
        for index in (8, 9):
            for field, value in (("source_id", 0), ("event", "0x501F"), ("internal_id", 31)):
                changed = deepcopy(self.mapping)
                changed["buttons"][index][field] = value
                with self.subTest(index=index, field=field), self.assertRaises(ValueError):
                    firmware.validate_mapping(changed)

    def test_guessed_codes_and_missing_evidence_are_rejected(self):
        for field, value in (("physical_mapping_status", "unverified"), ("firmware_status", "unverified"), ("provenance", [])):
            changed = deepcopy(self.mapping)
            changed["buttons"][3][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                firmware.validate_mapping(changed)

    def test_inverse_address_raw_command_and_event_disagreement_fail(self):
        for field, value in (
            ("nec_inverse_command", "0x00"), ("nec_address_bytes", ["0x33", "0xFD"]),
            ("decoder_command", "0x00"), ("decoder_address", "0xEE32"),
            ("event", "0x701A"), ("event", "0x501B"), ("source_id", True),
            ("nec_command", True),
        ):
            changed = deepcopy(self.mapping)
            changed["buttons"][3][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                firmware.validate_mapping(changed)

    def test_changing_capture_with_consistent_bit_order_still_fails(self):
        changed = deepcopy(self.mapping)
        changed["buttons"][3].update({"nec_command": "0x2A", "nec_inverse_command": "0xD5", "decoder_command": "0x54"})
        with self.assertRaisesRegex(ValueError, "capture"):
            firmware.validate_mapping(changed)

    def test_missing_active_capture_remains_a_release_block(self):
        row = self.mapping["buttons"][7]
        row["physical_mapping_status"] = "unverified"
        for field in firmware.CODE_FIELDS:
            row[field] = None
        self.assertEqual(firmware.validate_mapping(self.mapping), ["7"])
        with self.assertRaises(firmware.ReleaseBlockedError):
            firmware.require_approved_release(self.mapping)


if __name__ == "__main__":
    unittest.main()
