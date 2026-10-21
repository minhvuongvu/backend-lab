"""Integrity checker skeleton: verify invariants after a run (especially after fault injection).

Example invariant (matches the scaffold's Item contract): every create the client saw acknowledged
(HTTP 201) is stored exactly once. Whether unacknowledged-but-stored rows are allowed depends on the
topic's guarantees (01-research.html §9), so they are reported, not judged.

How it works:
  1. Count acknowledged creates in the k6 raw CSV of this run (http_reqs, status=201, name="POST /items").
  2. Query PostgreSQL (via `docker compose exec postgres psql`) for rows written by this run
     (payload starts with "<testid>:") - total rows and distinct ids.
  3. missing = acknowledged - distinct_stored (if > 0), duplicates = total - distinct.
Count-based on purpose: per-id tags in k6 would explode metric cardinality in Prometheus. When a topic
needs per-id detail, have the app log acknowledged ids, or record ids through a dedicated endpoint.

Usage (from experiments/):
  python3 checker/integrity_check.py --testid before-F1-1 --k6-csv ../results/raw/before-F1-1-<ts>.k6.csv \
      --out ../results/raw/before-F1-1-<ts>-integrity.json
Exit code 0 = invariant holds, 1 = violated (the JSON says how), 2 = could not check.
REPLACE the SQL and the invariant with the topic's own (01-research.html §10, 04 §4.7) and test the
checker first on deliberately broken data.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone


def acknowledged_from_k6(path, name):
    ok = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("metric_name") != "http_reqs" or row.get("name") != name:
                continue
            if row.get("status") == "201":
                ok += int(float(row.get("metric_value") or 1))
    return ok


def stored_counts(testid, service, db, user):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", testid):
        raise ValueError(f"unsafe testid: {testid!r}")
    sql = f"SELECT count(*), count(DISTINCT id) FROM item WHERE payload LIKE '{testid}:%'"
    cmd = ["docker", "compose", "exec", "-T", service, "psql", "-U", user, "-d", db, "-At", "-c", sql]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"psql failed: {out.stderr.strip()}")
    total, distinct = out.stdout.strip().split("|")
    return int(total), int(distinct)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--testid", required=True)
    p.add_argument("--k6-csv", required=True)
    p.add_argument("--request-name", default="POST /items")
    p.add_argument("--service", default="postgres")
    p.add_argument("--db", default="lab")
    p.add_argument("--user", default="lab")
    p.add_argument("--out", required=True)
    a = p.parse_args()

    try:
        acked = acknowledged_from_k6(a.k6_csv, a.request_name)
        total, distinct = stored_counts(a.testid, a.service, a.db, a.user)
    except Exception as exc:  # report, never guess
        print(f"integrity check could not run: {exc}", file=sys.stderr)
        sys.exit(2)

    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "testid": a.testid,
        "invariant": "every acknowledged create is stored exactly once",
        "acknowledged": acked,
        "stored_rows": total,
        "stored_distinct_ids": distinct,
        "missing": max(acked - distinct, 0),
        "duplicates": total - distinct,
        "unacknowledged_but_stored": max(distinct - acked, 0),
    }
    result["holds"] = result["missing"] == 0 and result["duplicates"] == 0
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))
    sys.exit(0 if result["holds"] else 1)


if __name__ == "__main__":
    main()
