"""Run local RC2 instruction-execution suites with user-supplied firmware.

Neither input image is written. JSON reports contain evidence and addresses,
not firmware bytecode or extracted RAM blobs. Hardware remains untested.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from firmware_patch import EXPECTED_RC2, build
from test_support import protect_inputs, runtime_versions


def text_sha256(path: Path) -> str:
    """Bind portable UTF-8 source/report text independently of Git line endings."""
    return hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()


def validate_report(name: str, report: dict, original_hash: str) -> None:
    """Reject stale SK1/incomplete reports as well as the wrong image identity."""
    assert report['status'] == 'PASS'
    assert report['patched_sha256'] == EXPECTED_RC2
    assert report['original_sha256'] == original_hash
    if name == 'verify_dispatcher_rc2.py':
        assert report['all_16bit_non_target_trampoline_cases'] == 65528
        assert report['baseline_equivalence_cases'] == 112512
        assert report['new_command_cases'] == 384
        assert report['extended_candidate_cases'] == 8192
        assert report['amp_then_cd_without_ram_reset_cases'] == 64
        assert len(report['captured_frame_to_source_cases']) == 8
    elif name == 'verify_transitions_rc2.py':
        assert report['native_source_full_transition_equivalence_cases'] == 1280
        assert report['in_flight_latest_request_cases'] == 1024
        assert report['all_initial_and_target_source_pairs'] == 128
        assert len(report['persistence_save_restore_cases']) == 8
        assert len(report['rapid_repeated_requests']) == 8
        assert len(report['immediate_different_command_pairs']) == 56
    else:
        raise ValueError(f'Unknown suite: {name}')


def main() -> None:
    if not __debug__:
        raise SystemExit('Run without python -O; verification assertions must remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'generated' / 'emulation')
    parser.add_argument('--collect-existing', action='store_true',
                        help='Collect existing PASS reports for this image and coverage; do not execute suites')
    args = parser.parse_args()
    original = args.original.read_bytes()
    candidate = args.candidate.read_bytes()
    assert candidate == build(original)[0], 'Candidate differs from reviewed RC2'
    suites = ('verify_dispatcher_rc2.py', 'verify_transitions_rc2.py')
    paths = [args.output / (Path(name).stem + '.json') for name in suites]
    summary_path = args.output / 'emulation_verification_rc2.json'
    for path in (*paths, summary_path):
        protect_inputs(path, args.original, args.candidate)
    args.output.mkdir(parents=True, exist_ok=True)
    reports = []
    for name, path in zip(suites, paths):
        if not args.collect_existing:
            subprocess.run([
                sys.executable, str(HERE / name), '--original', str(args.original),
                '--candidate', str(args.candidate), '--output', str(path),
            ], check=True)
        report = json.loads(path.read_text(encoding='utf-8'))
        validate_report(name, report, hashlib.sha256(original).hexdigest())
        reports.append({
            'suite': name,
            'script_sha256': text_sha256(HERE / name),
            'report': path.name,
            'report_sha256': text_sha256(path),
            'status': report['status'],
        })
    assert args.original.read_bytes() == original, 'Original image changed during validation'
    assert args.candidate.read_bytes() == candidate, 'Candidate changed during validation'
    summary = {
        'status': 'PASS',
        'release': 'SK2-RC2',
        'original_sha256': hashlib.sha256(original).hexdigest(),
        'patched_sha256': EXPECTED_RC2,
        'candidate_size': len(candidate),
        'collection_mode': 'existing_reports' if args.collect_existing else 'execute_suites',
        'hash_representation': 'UTF-8 text with CRLF normalized to LF',
        'source_hash_binding': (
            'Current source tree. Existing report image identities and coverage were checked; suites were not rerun by this collection.'
            if args.collect_existing else
            'Source tree used for the suite executions in this run.'
        ),
        'runtime_versions': runtime_versions(),
        'suites': reports,
        'supporting_file_sha256': {
            str(path.relative_to(ROOT)).replace('\\', '/'):
                text_sha256(path)
            for path in (
                HERE / 'emulate_startup.py', HERE / 'test_support.py',
                HERE / 'run_rc2_validation.py', ROOT / 'firmware_patch.py',
                ROOT / 'qualify_rc2.py',
                ROOT / 'handler' / 'handler_sk2.asm',
                ROOT / 'data' / 'ir_mapping.json', ROOT / 'requirements-emulation.txt',
                HERE / 'review_rc2.py',
            ) if path.is_file()
        },
        'hardware_validation': 'NOT_PERFORMED',
        'limitations': 'Finite emulator scenarios with explicit hardware-call stubs; no physical amplifier, updater, or recovery validation.',
    }
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
