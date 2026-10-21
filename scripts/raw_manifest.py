#!/usr/bin/env python3
"""Keep per-request raw samples out of git but accountable (standard library only).

Full k6 samples (`k6 run --out csv`) are ~100 bytes per request: one 2-minute run at 2000 req/s is ~95 MB,
more than GitHub accepts comfortably (warning at 50 MB, hard limit 100 MB). So they live in
`topics/<slug>/results/raw-samples/` (gitignored), always gzipped, and only `MANIFEST.json` is committed:
for every file its name, size, sha256, row count, creation time, producing command and k6 testid. Every number
in 05/06 can then be traced to a file whose exact bytes are pinned, even on a machine that does not have it.

  # gzip every plain *.csv in the folder, then rewrite MANIFEST.json (run after each `make run`)
  python3 scripts/raw_manifest.py update topics/<slug>/results/raw-samples --cmd "make run IMPL=a SCENARIO=S1 RUN=1"

  # check local files against the manifest (exit 1 on a hash/size mismatch; --strict also fails on
  # files missing locally or not listed)
  python3 scripts/raw_manifest.py verify topics/<slug>/results/raw-samples [--strict]

Entries of files that are not present locally are kept (they were produced on another machine or deleted to
save space); the manifest is the record that they existed.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

MANIFEST = "MANIFEST.json"
CHUNK = 1 << 20
# <impl>-<scenario>-<run>-<ts>.<kind>.csv.gz; the k6 testid is <impl>-<scenario>-<run>
NAME_RE = re.compile(r"^(?P<testid>.+-[^-]+-[^-]+)-(?P<ts>\d{8}T\d{6}Z)\b")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def count_rows(path: Path) -> int:
    """Data rows (lines minus the CSV header) of a .csv or .csv.gz, streamed."""
    opener = gzip.open if path.name.endswith(".gz") else open
    lines = 0
    last = b"\n"
    with opener(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            lines += block.count(b"\n")
            last = block[-1:]
    if last != b"\n":
        lines += 1  # final line without a trailing newline
    return max(lines - 1, 0)


def gzip_file(src: Path) -> Path:
    """src.csv -> src.csv.gz (reproducible: no name/mtime in the gzip header), then delete src."""
    dst = src.with_name(src.name + ".gz")
    if dst.exists():
        sys.exit(f"error: {dst.name} already exists; refusing to overwrite raw data (remove one of them by hand)")
    tmp = dst.with_name(dst.name + ".part")
    with src.open("rb") as fin, tmp.open("wb") as raw, \
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as fout:
        shutil.copyfileobj(fin, fout, CHUNK)
    tmp.replace(dst)
    src.unlink()
    return dst


def load(folder: Path) -> dict:
    p = folder / MANIFEST
    if not p.exists():
        return {"files": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save(folder: Path, manifest: dict) -> None:
    manifest["files"].sort(key=lambda e: e["name"])
    text = json.dumps({"version": 1, **{k: v for k, v in manifest.items() if k != "version"}},
                      indent=2, ensure_ascii=False) + "\n"
    (folder / MANIFEST).write_text(text, encoding="utf-8", newline="\n")


def data_files(folder: Path):
    return sorted(p for p in folder.iterdir() if p.is_file() and p.name != MANIFEST and not p.name.startswith("."))


def cmd_update(args) -> int:
    folder = Path(args.dir)
    folder.mkdir(parents=True, exist_ok=True)
    fresh = set()
    for p in sorted(folder.glob("*.csv")):
        fresh.add(gzip_file(p).name)
        print(f"gzipped {p.name} -> {p.name}.gz")
    manifest = load(folder)
    entries = {e["name"]: e for e in manifest["files"]}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    added = changed = 0
    for p in data_files(folder):
        if p.name.endswith(".part"):
            continue
        size = p.stat().st_size
        old = entries.get(p.name)
        if old and old.get("bytes") == size and not args.rehash:
            continue  # same size: trust the recorded hash (verify re-checks it); keeps update cheap
        digest = sha256(p)
        if old and old.get("sha256") == digest:
            continue
        if old and p.name not in fresh:
            print(f"WARN {p.name}: content differs from the manifest; recording the new hash "
                  f"(raw data should never change — check why)", file=sys.stderr)
            changed += 1
        else:
            added += 1
        m = NAME_RE.match(p.name)
        entry = {
            "name": p.name,
            "bytes": size,
            "sha256": digest,
            "rows": count_rows(p) if ".csv" in p.name else None,
            "created": (old or {}).get("created", now),
            "command": args.cmd if args.cmd is not None else (old or {}).get("command", ""),
            "testid": args.testid or (m.group("testid") if m else (old or {}).get("testid", "")),
        }
        entries[p.name] = entry
    manifest["files"] = list(entries.values())
    save(folder, manifest)
    missing = sum(1 for e in manifest["files"] if not (folder / e["name"]).exists())
    print(f"{folder / MANIFEST}: {len(manifest['files'])} file(s), {added} added, {changed} changed, "
          f"{missing} not present locally")
    return 0


def cmd_verify(args) -> int:
    folder = Path(args.dir)
    if not (folder / MANIFEST).exists():
        print(f"error: {folder / MANIFEST} not found", file=sys.stderr)
        return 1
    manifest = load(folder)
    listed = {e["name"] for e in manifest["files"]}
    bad = absent = 0
    for e in manifest["files"]:
        p = folder / e["name"]
        if not p.exists():
            absent += 1
            print(f"not present locally: {e['name']}")
            continue
        size = p.stat().st_size
        if size != e.get("bytes") or sha256(p) != e.get("sha256"):
            bad += 1
            print(f"MISMATCH {e['name']}: bytes {size} vs {e.get('bytes')} (manifest); sha256 differs")
        else:
            print(f"ok   {e['name']}")
    unlisted = [p.name for p in data_files(folder) if p.name not in listed]
    for name in unlisted:
        print(f"not in manifest: {name} (run: raw_manifest.py update {folder})")
    print(f"{len(listed)} listed, {bad} mismatched, {absent} not present locally, {len(unlisted)} not in manifest")
    if bad or (args.strict and (absent or unlisted)):
        return 1
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd_name", required=True)
    u = sub.add_parser("update", help="gzip plain *.csv, then rewrite MANIFEST.json")
    u.add_argument("dir")
    u.add_argument("--cmd", help="producing command recorded for new/changed entries")
    u.add_argument("--testid", help="k6 testid (default: parsed from <impl>-<scenario>-<run>-<ts>.*)")
    u.add_argument("--rehash", action="store_true", help="re-hash files even when the size is unchanged")
    u.set_defaults(func=cmd_update)
    v = sub.add_parser("verify", help="check local files against MANIFEST.json")
    v.add_argument("dir")
    v.add_argument("--strict", action="store_true", help="also fail on files missing locally or not listed")
    v.set_defaults(func=cmd_verify)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
