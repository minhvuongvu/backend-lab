"""Size guard of scripts/hooks/pre-commit, run against a throwaway git repo."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from _helpers import ENV, REPO, find_bash

BASH = find_bash()
GIT = shutil.which("git")


@unittest.skipUnless(BASH and GIT, "needs bash and git")
class SizeGuardTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="lab-hook-"))
        self.git("init", "-q")
        shutil.copy2(REPO / "scripts/hooks/pre-commit", self.dir / "pre-commit")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def git(self, *args):
        subprocess.run([GIT, *args], cwd=self.dir, check=True, capture_output=True)

    def stage(self, rel, size):
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * size)
        self.git("add", "-f", rel)

    def hook(self):
        # Paths outside the hook's filter (notes/, data/) stop it right after the guard, so no lab checks run.
        return subprocess.run([BASH, "pre-commit"], cwd=self.dir, capture_output=True, text=True,
                              env={**ENV, "LAB_MAX_FILE_MB": "1"})

    def test_small_file_passes(self):
        self.stage("notes/a.txt", 1000)
        r = self.hook()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_large_file_fails_with_guidance(self):
        self.stage("data/big.csv", 2 * 1024 * 1024)
        r = self.hook()
        self.assertEqual(r.returncode, 1)
        self.assertIn("data/big.csv (2 MB)", r.stdout)
        self.assertIn("raw-samples", r.stdout)
        self.assertIn("raw_manifest.py update", r.stdout)

    def test_lfs_tracked_large_file_passes(self):
        (self.dir / ".gitattributes").write_text("data/*.bin filter=lfs diff=lfs merge=lfs -text\n")
        self.stage("data/big.bin", 2 * 1024 * 1024)
        r = self.hook()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_raw_samples_never_committed_even_small(self):
        self.stage("topics/x/results/raw-samples/before-S1-1-20261021T101500Z.k6.csv.gz", 100)
        r = self.hook()
        self.assertEqual(r.returncode, 1)
        self.assertIn("raw-samples/ is local only", r.stdout)


if __name__ == "__main__":
    unittest.main()
