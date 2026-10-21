"""Shared helpers for backend-lab script tests (standard library only).

Layout: hub pages live in hub/ (hub/roadmap.html, hub/insights.html, …; see scripts/_paths.py).

Scripts resolve the repo root from their own location (ROOT = Path(__file__).parent.parent), so tests
copy the scripts they exercise into a temporary repo skeleton and run them there. No script needs a
"--root" switch and the real repository is never touched.
"""
import csv
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def load_module(name):
    """Import scripts/<name>.py as a module (for pure-function tests)."""
    spec = importlib.util.spec_from_file_location(f"lab_{name}", SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TempRepo:
    """A throwaway repo skeleton with selected scripts copied into <tmp>/scripts."""

    def __init__(self, scripts=(), copy_paths=()):
        self.dir = Path(tempfile.mkdtemp(prefix="lab-test-"))
        (self.dir / "scripts").mkdir()
        (self.dir / "hub").mkdir()  # exists in the real repo; the builders do not create it themselves
        # Every Python script imports scripts/_paths.py (ROOT, hub/ locations, hubify), so it always comes along.
        for name in {*scripts, *(["_paths.py"] if (SCRIPTS / "_paths.py").exists() else [])}:
            shutil.copy2(SCRIPTS / name, self.dir / "scripts" / name)
        for rel in copy_paths:
            src = REPO / rel
            dst = self.dir / rel
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    def path(self, rel):
        return self.dir / rel

    def write(self, rel, text):
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
        return p

    def csv(self, rel):
        with (self.dir / rel).open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def py(self, script, *args):
        return subprocess.run([sys.executable, str(self.dir / "scripts" / script), *args], cwd=self.dir,
                              env=ENV, capture_output=True, text=True, encoding="utf-8")

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def find_bash():
    """Git Bash / POSIX bash. On Windows avoid System32\\bash.exe (WSL launcher)."""
    if os.environ.get("LAB_BASH"):
        return os.environ["LAB_BASH"]
    candidates = [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"]
    for c in candidates:
        if os.path.exists(c):
            return c
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        return found
    return None
