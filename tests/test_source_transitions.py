"""Optional entry point for real instruction tests using local, private images."""

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import firmware_patch as firmware


@unittest.skipUnless(
    os.environ.get("QUAD3_RUN_LOCAL_EMULATION") == "1",
    "Real instruction tests need local stock/candidate images and emulator dependencies; see tests/local/README.md",
)
class SourceTransitionIntegrationTests(unittest.TestCase):
    def test_real_dispatcher_worker_routing_and_persistence(self):
        """Opt-in invocation runs the complete native suites, not a Python FSM model."""
        original = Path(os.environ["QUAD3_ORIGINAL"])
        candidate = Path(os.environ["QUAD3_CANDIDATE"])
        output = firmware.HERE / "generated" / "integration"
        subprocess.run([
            sys.executable, str(firmware.HERE / "tests" / "local" / "run_rc2_validation.py"),
            "--original", str(original), "--candidate", str(candidate), "--output", str(output),
        ], check=True)
        report = json.loads((output / "emulation_verification_rc2.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["patched_sha256"], firmware.EXPECTED_RC2)
        self.assertEqual(report["hardware_validation"], "NOT_PERFORMED")


if __name__ == "__main__":
    unittest.main()
