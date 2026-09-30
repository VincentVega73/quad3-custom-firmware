"""Guard the tracked publication surface; this is not a copyright-content audit."""

from pathlib import PurePosixPath
import shutil
import subprocess
import unittest

import firmware_patch as firmware


@unittest.skipUnless(shutil.which("git"), "Git is needed to inspect tracked publication files")
class RepositoryPolicyTests(unittest.TestCase):
    def test_tracked_files_exclude_images_archives_and_private_output(self):
        result = subprocess.run(
            ["git", "ls-files", "-z"], cwd=firmware.HERE, capture_output=True, check=True,
        )
        names = result.stdout.decode("utf-8").split("\0")
        forbidden_directories = {"firmware", "vendor", "dumps", "generated"}
        forbidden_suffixes = {".bin", ".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".xz"}
        for name in filter(None, names):
            relative = PurePosixPath(name)
            with self.subTest(path=name):
                self.assertFalse(forbidden_directories.intersection(part.lower() for part in relative.parts[:-1]))
                self.assertNotIn(relative.suffix.lower(), forbidden_suffixes)
                # This repository's approved publication surface is UTF-8 text.
                # Human review is still needed for embedded proprietary material.
                (firmware.HERE / name).read_text(encoding="utf-8", errors="strict")
