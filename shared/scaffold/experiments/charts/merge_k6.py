"""Concatenate per-run k6 CSV files (same header) into one file for `stats.py summarize`.

Usage: python3 charts/merge_k6.py --glob "../results/raw/*.k6.csv" --exclude pilot --out ../results/analysis/k6-all.csv
Streams line by line, so multi-GB inputs are fine. Output goes to results/analysis/ (derived data),
never into results/raw/ (raw data is not edited or regenerated).
"""

import argparse
import glob
import os
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--glob", required=True)
    p.add_argument("--exclude", action="append", default=[], help="skip files whose name contains this text")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    files = sorted(f for f in glob.glob(a.glob) if not any(x in os.path.basename(f) for x in a.exclude))
    if not files:
        sys.exit(f"no files match {a.glob}")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    header = None
    with open(a.out, "w", encoding="utf-8", newline="") as out:
        for path in files:
            with open(path, encoding="utf-8", newline="") as f:
                first = f.readline()
                if header is None:
                    header = first
                    out.write(first)
                elif first != header:
                    sys.exit(f"header mismatch in {path}")
                for line in f:
                    out.write(line)
    print(f"merged {len(files)} file(s) -> {a.out}")


if __name__ == "__main__":
    main()
