"""Statically qualify the exact SK2-RC2 candidate against its pinned stock image.

This verifies bytes, hashes, layout, and decoded branch destinations. It does
not execute the firmware, access hardware, or prove compatibility/recovery.
Run the separate local instruction-execution suites before hardware testing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

import firmware_patch as patch


def decode_wide_branch(data: bytes, address: int) -> int:
    """Decode a Thumb-2 unconditional B.W or BL target, including sign extension."""
    if len(data) != 4 or address & 1:
        raise ValueError("A wide Thumb branch requires four bytes at a halfword address")
    first, second = struct.unpack("<HH", data)
    if first & 0xF800 != 0xF000 or second & 0xD000 not in (0x9000, 0xD000):
        raise ValueError("Instruction is not an unconditional Thumb B.W or BL")
    sign = (first >> 10) & 1
    i1 = 1 ^ ((second >> 13) & 1) ^ sign
    i2 = 1 ^ ((second >> 11) & 1) ^ sign
    immediate = (sign << 24) | (i1 << 23) | (i2 << 22) | ((first & 0x3FF) << 12) | ((second & 0x7FF) << 1)
    if sign:
        immediate -= 1 << 25
    return address + 4 + immediate


def changed_ranges(original: bytes, candidate: bytes) -> list[dict[str, str]]:
    if len(candidate) < len(original):
        raise ValueError("Candidate truncates the stock image")
    ranges = []
    start = None
    for offset, (before, after) in enumerate(zip(original, candidate)):
        if before != after and start is None:
            start = offset
        elif before == after and start is not None:
            ranges.append({"offset": hex(start), "end_exclusive": hex(offset)})
            start = None
    if start is not None:
        ranges.append({"offset": hex(start), "end_exclusive": hex(len(original))})
    if len(candidate) > len(original):
        ranges.append({"offset": hex(len(original)), "end_exclusive": hex(len(candidate))})
    return ranges


def qualify(original: bytes, candidate: bytes) -> dict:
    patch.validate_original(original)
    if len(candidate) != patch.RC2_SIZE:
        raise ValueError(f"RC2 size mismatch: {len(candidate)}; expected {patch.RC2_SIZE}")
    if patch.sha256(candidate) != patch.EXPECTED_RC2:
        raise ValueError("RC2 SHA256 mismatch")
    if candidate[:patch.VECTOR_TABLE_SIZE] != original[:patch.VECTOR_TABLE_SIZE]:
        raise ValueError("Vector table changed")
    if candidate[patch.HOOK:patch.HOOK + 4] != patch.BRANCH:
        raise ValueError("Dispatcher branch bytes mismatch")
    if candidate[patch.ORIGINAL_SIZE:] != patch.PAYLOAD:
        raise ValueError("Handler bytes mismatch")
    end = patch.BASE + len(candidate)
    if end > patch.FLASH_LIMIT_EXCLUSIVE:
        raise ValueError("Candidate exceeds the minimum compatible flash model")
    expected_ranges = [
        {"offset": hex(patch.HOOK), "end_exclusive": hex(patch.HOOK + 4)},
        {"offset": hex(patch.ORIGINAL_SIZE), "end_exclusive": hex(patch.RC2_SIZE)},
    ]
    actual_ranges = changed_ranges(original, candidate)
    if actual_ranges != expected_ranges:
        raise ValueError("Unexpected changed ranges")
    rebuilt, _, _ = patch.build(original)
    if candidate != rebuilt:
        raise ValueError("Candidate differs from a deterministic rebuild")
    handler_start = patch.BASE + patch.ORIGINAL_SIZE
    # Offsets refer to the frozen 120-byte instruction sequence, followed by a
    # single 32-bit literal. Pinning the whole payload protects these boundaries.
    branches = (
        (patch.BASE + patch.HOOK, patch.BRANCH, handler_start, "handler entry"),
        (handler_start + 72, patch.PAYLOAD[72:76], 0x0801334A, "stock fallback"),
        (handler_start + 108, patch.PAYLOAD[108:112], 0x080131F8, "housekeeping call"),
        (handler_start + 116, patch.PAYLOAD[116:120], 0x080134D4, "native source tail"),
    )
    decoded = []
    for address, instruction, expected, purpose in branches:
        target = decode_wide_branch(instruction, address)
        if target != expected:
            raise ValueError(f"Incorrect {purpose} branch target")
        decoded.append({"address": hex(address), "target": hex(target), "purpose": purpose})
    literal = struct.unpack("<I", patch.PAYLOAD[patch.HANDLER_CODE_SIZE:])[0]
    if literal != 0x20000ED3 or (handler_start + patch.HANDLER_CODE_SIZE) % 4:
        raise ValueError("Requested-source literal is invalid or misaligned")
    return {
        "schema_version": 1,
        "release": "SK2-RC2",
        "status": "PASS",
        "scope": "Static binary qualification; separate emulator and hardware validation required",
        "original_sha256": patch.sha256(original),
        "candidate_sha256": patch.sha256(candidate),
        "candidate_size": len(candidate),
        "last_address": hex(end - 1),
        "end_exclusive": hex(end),
        "remaining_bytes_under_minimum_compatible_model": patch.FLASH_LIMIT_EXCLUSIVE - end,
        "changed_ranges": actual_ranges,
        "decoded_wide_branches": decoded,
        "checks": {
            "original_size_hash_hook_and_decoder_pairs": True,
            "candidate_size_and_golden_hash": True,
            "vector_table_unchanged": True,
            "hook_and_handler_exact": True,
            "no_unexpected_stock_changes": True,
            "deterministic_rebuild": True,
            "flash_boundary": True,
            "wide_branch_targets": True,
            "literal_value_and_alignment": True,
        },
        "instruction_emulation": "Not performed by this tool; see tests/local/",
        "physical_rc2_tested": False,
        "actual_mcu_identification": "Not physically read; flash boundary is a minimum compatible model",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Exact stock v1.14j image")
    parser.add_argument("--candidate", type=Path, default=patch.HERE / "generated" / patch.OUTPUT_NAME)
    parser.add_argument("--report", type=Path, help="Optional local JSON qualification report")
    args = parser.parse_args(argv)
    try:
        if patch._same_path(args.input, args.candidate):
            raise ValueError("Candidate and original must be different files")
        if args.report and (patch._same_path(args.report, args.input) or patch._same_path(args.report, args.candidate)):
            raise ValueError("Report must not overwrite either firmware input")
        patch.require_approved_release(patch.load_mapping())
        report = qualify(args.input.read_bytes(), args.candidate.read_bytes())
        serialized = json.dumps(report, indent=2) + "\n"
        if args.report:
            patch.write_new_or_identical(args.report, serialized.encode("utf-8"))
        print(serialized, end="")
        return 0
    except patch.ReleaseBlockedError as exc:
        print(f"NOT QUALIFIED: {exc}", file=sys.stderr)
        return 3
    except (OSError, ValueError, TypeError, struct.error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
