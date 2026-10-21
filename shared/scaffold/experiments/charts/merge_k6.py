"""Concatenate per-run k6 CSV files (same header, plain or .gz) into one file, for ad-hoc analysis.

`make report` does not need it: `stats.py summarize --input` and `plot.py cdf --k6` take many files.
Usage: python3 charts/merge_k6.py --glob "../results/raw-samples/*.k6.csv.gz" --exclude pilot            --out ../results/raw-samples/merged-all.csv.gz
Streams line by line, so multi-GB inputs are fine. A merged file is as large as all runs together: write it
gzipped into raw-samples/ (gitignored), never into results/raw/ or another committed folder.
"""

import argparse
import glob
import gzip
import os
import sys


def open_text(path, mode):
    if path.endswith(".gz"):
        return gzip.open(path, mode + "t", encoding="utf-8", newline="")
    return open(path, mode, encoding="utf-8", newline="")


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
    with open_text(a.out, "w") as out:
        for path in files:
            with open_text(path, "r") as f:
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
