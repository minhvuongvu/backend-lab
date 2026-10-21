#!/usr/bin/env python3
"""Statistics helpers for backend-lab experiments (standard library only).

Subcommands
-----------
plan-order    Blocked, seeded randomisation of the run order (impl x scenario x run).
steady-state  Where warmup ends: MSER-5 truncation point (primary) + rolling coefficient-of-variation check.
summarize     Per-run latency statistics from a k6 CSV (or a generic long CSV), then per impl x scenario
              aggregates with a cluster-bootstrap CI over runs.
compare       Each implementation vs the baseline (`before`) on one run-level metric:
              median difference / ratio with bootstrap CI, Mann-Whitney U, Cliff's delta, verdict.

Methodology (why it is done this way)
-------------------------------------
* The unit of replication is the RUN, not the request. Requests inside one run share the same JVM,
  JIT state, caches, GC history and machine noise, so they are not independent. Treating 1M requests
  as 1M independent samples makes confidence intervals absurdly narrow. Hence the bootstrap resamples
  whole runs (cluster bootstrap) and the tests compare run-level values.
* Percentiles are never averaged across runs. The mean of per-run p99 values is not the p99 of anything
  and is dominated by the worst run. We report the median of run-level percentiles (robust to one bad
  run) with IQR and bootstrap CI, and separately the pooled-sample percentile (all requests together).
* Latency distributions are skewed and heavy-tailed, and n (runs) is small (3-10), so normality cannot
  be checked or assumed. A t-test on means would be dominated by outliers. Mann-Whitney U is rank based
  (no distribution assumption; exact p-values for small n), and Cliff's delta is the matching effect
  size: P(X > Y) - P(X < Y), interpretable as "how often a run of A is slower than a run of before".
* Statistical significance is not practical significance: a 1% p99 change can be "significant" and
  irrelevant. `compare` therefore requires both a CI that excludes "no change" AND an effect above
  --min-effect before calling something better/worse.
* With n < 5 runs per group the bootstrap CI and p-values are coarse (exact Mann-Whitney with 3 vs 3 can
  never go below p = 0.1); the output flags this.
* Percentile estimation uses linear interpolation between order statistics (Hyndman-Fan type 7).
  p99.9 needs well over 1000 samples per run to mean anything; `n` is reported so this can be checked.

Usage examples
--------------
  # 1. Randomised, blocked run order (each block runs every impl once) -> follow it when executing
  python3 scripts/stats.py plan-order --impls before,A,B --scenarios S1,F1 --runs 5 --seed 42 \\
      --out topics/<slug>/results/raw/run-order.csv

  # 2. Where does warmup end? (e.g. throughput or p99 per interval exported with prom_export.py / k6).
  #    Use the larger of the two answers, and the same warmup for every impl.
  python3 scripts/stats.py steady-state --input rps.csv --time-col unix_ts --value-col value \\
      --window 6 --cov 0.05 --consecutive 3

  # 3. Summarise k6 raw samples (k6 run --out csv=... --tag testid=<impl>-<scenario>-<run>), one gzip per run,
  #    no merge step needed: every --input file is streamed in turn.
  python3 scripts/stats.py summarize --input topics/<slug>/results/raw-samples/*.k6.csv.gz --format k6 \\
      --metric http_req_duration --skip-seconds 30 --out topics/<slug>/results/analysis/runs.csv

  # 4. Compare every impl with before on run-level p99 (lower is better), 5% practical threshold
  python3 scripts/stats.py compare --summary topics/<slug>/results/analysis/runs.csv \\
      --baseline before --metric p99 --min-effect 0.05
"""

from __future__ import annotations

import argparse
import csv
import gzip
import itertools
import json
import math
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path


def open_text(path):
    """Open a CSV for streaming text reads; *.gz (results/raw-samples/*.csv.gz) is decompressed on the fly."""
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", newline="", encoding="utf-8")
    return open(path, newline="", encoding="utf-8")

PERCENTILES = [("p50", 50.0), ("p90", 90.0), ("p95", 95.0), ("p99", 99.0), ("p99_9", 99.9)]


# ----------------------------------------------------------------------------- helpers

def percentile(sorted_vals: list[float], q: float) -> float:
    """Linear interpolation between closest ranks (Hyndman-Fan type 7, numpy default)."""
    n = len(sorted_vals)
    if n == 0:
        return math.nan
    if n == 1:
        return sorted_vals[0]
    pos = (n - 1) * q / 100.0
    lo = math.floor(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def quantiles_of(values: list[float], qs=(25.0, 75.0)) -> list[float]:
    s = sorted(values)
    return [percentile(s, q) for q in qs]


def bootstrap_ci(groups: list[list[float]], stat, resamples: int, rng: random.Random, alpha=0.05):
    """Percentile bootstrap: resample each group independently (with replacement) and apply stat(*groups)."""
    if any(len(g) == 0 for g in groups):
        return math.nan, math.nan
    estimates = []
    for _ in range(resamples):
        sample = [[g[rng.randrange(len(g))] for _ in g] for g in groups]
        v = stat(*sample)
        if not math.isnan(v):
            estimates.append(v)
    if not estimates:
        return math.nan, math.nan
    estimates.sort()
    return percentile(estimates, 100 * alpha / 2), percentile(estimates, 100 * (1 - alpha / 2))


def fmt(v, digits=4):
    if isinstance(v, float):
        if math.isnan(v):
            return "nan"
        return f"{v:.{digits}g}"
    return str(v)


def write_csv(path: Path, rows: list[dict], columns: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (fmt(v, 10) if isinstance(v, float) else v) for k, v in r.items()})


def print_table(rows: list[dict], columns: list[str]):
    if not rows:
        print("(no rows)")
        return
    cells = [[fmt(r.get(c, "")) for c in columns] for r in rows]
    widths = [max(len(c), *(len(row[i]) for row in cells)) for i, c in enumerate(columns)]
    print("  ".join(c.ljust(w) for c, w in zip(columns, widths)))
    for row in cells:
        print("  ".join(v.ljust(w) for v, w in zip(row, widths)))


# ----------------------------------------------------------------------------- plan-order

def cmd_plan_order(args):
    out = Path(args.out)
    if out.exists() and not args.force:
        sys.exit(f"error: {out} exists; run order is raw data - use --force to overwrite")
    impls = [s.strip() for s in args.impls.split(",") if s.strip()]
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    rng = random.Random(args.seed)
    rows, seq = [], 0
    for scenario in scenarios:
        for block in range(1, args.runs + 1):
            order = impls[:]
            rng.shuffle(order)
            for impl in order:
                seq += 1
                rows.append({"seq": seq, "block": block, "scenario": scenario, "impl": impl, "run": block})
    write_csv(out, rows, ["seq", "block", "scenario", "impl", "run"])
    print(f"wrote {len(rows)} runs to {out} (seed={args.seed}); execute them in `seq` order")


# ----------------------------------------------------------------------------- steady-state

def cmd_steady_state(args):
    times, values = [], []
    with open_text(args.input) as fh:
        for row in csv.DictReader(fh):
            try:
                v = float(row[args.value_col])
            except (KeyError, ValueError):
                continue
            if math.isnan(v):
                continue
            times.append(row[args.time_col])
            values.append(v)
    # Primary: MSER-b (White 1997; MSER-5 is the usual batch size). Truncate d batches where
    # sum((Y_j - mean)^2) / (m - d)^2 over the remaining batch means is minimal (search d <= m/2).
    # It trades bias removed (dropping the transient) against variance added (fewer points) and,
    # unlike a CoV threshold, it catches slow monotone warmup trends.
    b = args.batch
    batches = [statistics.fmean(values[j:j + b]) for j in range(0, len(values) - b + 1, b)]
    mser_d, mser_best = 0, math.inf
    for d in range(0, len(batches) // 2 + 1):
        rest = batches[d:]
        if len(rest) < 2:
            break
        mu = statistics.fmean(rest)
        stat = sum((y - mu) ** 2 for y in rest) / (len(rest) ** 2)
        if stat < mser_best:
            mser_best, mser_d = stat, d
    mser_idx = mser_d * b
    print(f"MSER-{b}: truncate first {mser_idx} points (warmup ends at t={times[mser_idx]})"
          + ("  [warning: optimum at the search limit — run is probably too short]"
             if mser_d == len(batches) // 2 else ""))

    w, k = args.window, args.consecutive
    if len(values) < w + k - 1:
        sys.exit(f"error: need at least {w + k - 1} points, got {len(values)}")
    covs = []
    for i in range(len(values) - w + 1):
        win = values[i:i + w]
        m = statistics.fmean(win)
        covs.append(statistics.stdev(win) / abs(m) if m else math.inf)
    for i in range(len(covs) - k + 1):
        # Each window must be quiet AND the whole span must be flat: a slow warmup trend can have a low
        # CoV inside every short window while still drifting across them.
        span = values[i:i + w + k - 1]
        span_cov = statistics.stdev(span) / abs(statistics.fmean(span)) if statistics.fmean(span) else math.inf
        if all(c < args.cov for c in covs[i:i + k]) and span_cov < args.cov:
            print(f"CoV check: steady from t={times[i]} (point #{i}, {i} points of warmup); "
                  f"CoV of next {k} windows: {', '.join(f'{c:.3f}' for c in covs[i:i + k])}; span CoV {span_cov:.3f}")
            result = {"mser_warmup_points": mser_idx, "mser_warmup_end_time": times[mser_idx],
                      "cov_steady_from_time": times[i], "cov_steady_from_index": i, "window": w,
                      "cov_threshold": args.cov, "consecutive": k}
            break
    else:
        best = min(covs)
        print(f"CoV check: not reached: no {k} consecutive windows with CoV < {args.cov} (min CoV {best:.3f}). "
              "Lengthen the run, or the system never stabilises (investigate before measuring).")
        result = {"mser_warmup_points": mser_idx, "mser_warmup_end_time": times[mser_idx],
                  "cov_steady_from_time": None, "min_cov": best}
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2), encoding="utf-8")


# ----------------------------------------------------------------------------- summarize

def split_testid(testid: str):
    """'<impl>-<scenario>-<run>' -> (impl, scenario, run); impl may itself contain '-'."""
    parts = testid.rsplit("-", 2)
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def parse_extra_tags(extra: str) -> dict:
    tags = {}
    for kv in extra.split("&"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            tags[k] = v
    return tags


def read_samples(args):
    """Stream every input file; return {(impl, scenario, run): ([values], [ts], min_ts, max_ts)}."""
    data: dict[tuple, list] = {}
    skipped = 0
    for path in args.input:
        skipped += _read_sample_file(path, args, data)
    if skipped:
        print(f"note: skipped {skipped} rows without a parsable testid/value", file=sys.stderr)
    return data


def _read_sample_file(path, args, data):
    skipped = 0
    with open_text(path) as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None:
            print(f"note: {path} is empty", file=sys.stderr)
            return 0
        idx = {name: i for i, name in enumerate(header)}

        def col(row, name):
            i = idx.get(name)
            return row[i] if i is not None and i < len(row) else ""

        explicit = all(c in idx for c in ("impl", "scenario", "run"))
        if args.format == "k6":
            for need in ("metric_name", "metric_value"):
                if need not in idx:
                    sys.exit(f"error: {path} has no '{need}' column — is it `k6 run --out csv=...` output?")
        else:
            if not explicit or "value" not in idx:
                sys.exit("error: long format needs columns impl,scenario,run,value (optional: timestamp)")
        value_col = "metric_value" if args.format == "k6" else "value"
        ts_col = "timestamp" if "timestamp" in idx else None

        for row in reader:
            if args.format == "k6":
                if col(row, "metric_name") != args.metric:
                    continue
                if args.only_ok and col(row, "expected_response") not in ("", "true"):
                    continue
            if explicit:
                key = (col(row, "impl"), col(row, "scenario"), col(row, "run"))
            else:
                testid = col(row, "testid") or parse_extra_tags(col(row, "extra_tags")).get("testid", "")
                key = split_testid(testid) if testid else None
                if key is None:
                    skipped += 1
                    continue
            try:
                v = float(col(row, value_col))
            except ValueError:
                skipped += 1
                continue
            ts = None
            if ts_col:
                try:
                    ts = float(col(row, ts_col))
                except ValueError:
                    ts = None
            entry = data.get(key)
            if entry is None:
                entry = data[key] = [[], [], math.inf, -math.inf]  # values, (ts per value), min, max
            entry[0].append(v)
            if ts is not None:
                entry[1].append(ts)
                if ts < entry[2]:
                    entry[2] = ts
                if ts > entry[3]:
                    entry[3] = ts
    return skipped


def cmd_summarize(args):
    started = time.perf_counter()
    data = read_samples(args)
    if not data:
        sys.exit(f"error: no samples for metric '{args.metric}' in {', '.join(map(str, args.input))}")

    run_rows = []
    pooled: dict[tuple, list[float]] = defaultdict(list)
    for (impl, scenario, run), (vals, tss, tmin, tmax) in sorted(data.items()):
        if args.skip_seconds and tss:
            cutoff = tmin + args.skip_seconds
            vals = [v for v, t in zip(vals, tss) if t >= cutoff]
            tmin = cutoff
        if not vals:
            continue
        s = sorted(vals)
        row = {"impl": impl, "scenario": scenario, "run": run, "n": len(s), "mean": statistics.fmean(s)}
        for name, q in PERCENTILES:
            row[name] = percentile(s, q)
        row["max"] = s[-1]
        span = (tmax - tmin) if tss and tmax > tmin else math.nan
        # k6 CSV timestamps have 1 s resolution, so throughput over short runs is approximate.
        row["duration_s"] = span
        row["throughput_per_s"] = len(s) / span if span and not math.isnan(span) else math.nan
        run_rows.append(row)
        pooled[(impl, scenario)].extend(s)

    rng = random.Random(args.seed)
    group_rows = []
    by_group = defaultdict(list)
    for r in run_rows:
        by_group[(r["impl"], r["scenario"])].append(r)
    for (impl, scenario), runs in sorted(by_group.items()):
        g = {"impl": impl, "scenario": scenario, "runs": len(runs), "requests": sum(r["n"] for r in runs)}
        for metric in ("p50", "p95", "p99", "throughput_per_s"):
            vals = [r[metric] for r in runs if not math.isnan(r[metric])]
            if not vals:
                continue
            g[f"{metric}_median"] = statistics.median(vals)
            q1, q3 = quantiles_of(vals)
            g[f"{metric}_iqr"] = q3 - q1
            lo, hi = bootstrap_ci([vals], lambda x: statistics.median(x), args.resamples, rng)
            g[f"{metric}_ci_lo"], g[f"{metric}_ci_hi"] = lo, hi
        ps = sorted(pooled[(impl, scenario)])
        for name, q in PERCENTILES:
            g[f"pooled_{name}"] = percentile(ps, q)
        g["note"] = "few runs: CI coarse" if len(runs) < 5 else ""
        group_rows.append(g)

    run_cols = ["impl", "scenario", "run", "n", "mean"] + [n for n, _ in PERCENTILES] + ["max", "duration_s",
                                                                                         "throughput_per_s"]
    group_cols = ["impl", "scenario", "runs", "requests"]
    for metric in ("p50", "p95", "p99", "throughput_per_s"):
        group_cols += [f"{metric}_median", f"{metric}_iqr", f"{metric}_ci_lo", f"{metric}_ci_hi"]
    group_cols += [f"pooled_{n}" for n, _ in PERCENTILES] + ["note"]

    print(f"# per run ({args.metric}{', skipped first %ss' % args.skip_seconds if args.skip_seconds else ''})")
    print_table(run_rows, run_cols)
    print("\n# per impl x scenario (median of run-level values, 95% cluster-bootstrap CI over runs)")
    print_table(group_rows, ["impl", "scenario", "runs", "p50_median", "p95_median", "p99_median", "p99_ci_lo",
                             "p99_ci_hi", "pooled_p99", "note"])

    if args.out:
        out = Path(args.out)
        write_csv(out, run_rows, run_cols)
        groups_path = out.with_name(out.stem + ".groups.csv")
        write_csv(groups_path, group_rows, group_cols)
        print(f"\nwrote {out} and {groups_path}")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps({"metric": args.metric, "runs": run_rows, "groups": group_rows},
                                              indent=2, default=lambda v: None), encoding="utf-8")
    print(f"({time.perf_counter() - started:.2f}s)", file=sys.stderr)


# ----------------------------------------------------------------------------- compare

def rank_with_ties(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def mann_whitney(x: list[float], y: list[float]) -> tuple[float, float, str]:
    """Two-sided Mann-Whitney U. Returns (U for x, p, method)."""
    n1, n2 = len(x), len(y)
    ranks = rank_with_ties(x + y)
    r1 = sum(ranks[:n1])
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    if n1 <= 10 and n2 <= 10:
        # Exact permutation distribution of the rank sum (handles ties via mid-ranks).
        obs = abs(u1 - mu)
        total = extreme = 0
        for combo in itertools.combinations(ranks, n1):
            u = sum(combo) - n1 * (n1 + 1) / 2
            total += 1
            if abs(u - mu) >= obs - 1e-9:
                extreme += 1
        return u1, extreme / total, "exact"
    n = n1 + n2
    counts = defaultdict(int)
    for r in ranks:
        counts[r] += 1
    tie_term = sum(t ** 3 - t for t in counts.values()) / (n * (n - 1))
    sigma = math.sqrt(n1 * n2 / 12 * ((n + 1) - tie_term))
    if sigma == 0:
        return u1, 1.0, "normal"
    z = (abs(u1 - mu) - 0.5) / sigma
    p = math.erfc(max(z, 0) / math.sqrt(2))
    return u1, min(p, 1.0), "normal"


def cliffs_delta(x: list[float], y: list[float]) -> float:
    gt = sum(1 for a in x for b in y if a > b)
    lt = sum(1 for a in x for b in y if a < b)
    return (gt - lt) / (len(x) * len(y))


def cliffs_label(d: float) -> str:
    a = abs(d)
    if a < 0.147:
        return "negligible"
    if a < 0.33:
        return "small"
    if a < 0.474:
        return "medium"
    return "large"


def cmd_compare(args):
    groups: dict[tuple, list[float]] = defaultdict(list)
    with open_text(args.summary) as fh:
        reader = csv.DictReader(fh)
        if args.metric not in (reader.fieldnames or []):
            sys.exit(f"error: column '{args.metric}' not in {args.summary}; available: {reader.fieldnames}")
        for row in reader:
            try:
                v = float(row[args.metric])
            except ValueError:
                continue
            if not math.isnan(v):
                groups[(row["scenario"], row["impl"])].append(v)

    rng = random.Random(args.seed)
    scenarios = sorted({s for s, _ in groups})
    rows = []
    for scenario in scenarios:
        base = groups.get((scenario, args.baseline))
        if not base:
            print(f"warning: no baseline '{args.baseline}' runs for scenario {scenario}", file=sys.stderr)
            continue
        for (s, impl), vals in sorted(groups.items()):
            if s != scenario or impl == args.baseline:
                continue
            mb, mi = statistics.median(base), statistics.median(vals)
            diff = mi - mb
            ratio = mi / mb if mb else math.nan
            d_lo, d_hi = bootstrap_ci([vals, base], lambda a, b: statistics.median(a) - statistics.median(b),
                                      args.resamples, rng)
            r_lo, r_hi = bootstrap_ci([vals, base],
                                      lambda a, b: (statistics.median(a) / statistics.median(b)
                                                    if statistics.median(b) else math.nan),
                                      args.resamples, rng)
            _, p, method = mann_whitney(vals, base)
            delta = cliffs_delta(vals, base)

            # Direction: by default lower is better (latency); --higher-is-better for throughput.
            ci_excludes_one = not (math.isnan(r_lo) or (r_lo <= 1 <= r_hi))
            effect = abs(ratio - 1) if not math.isnan(ratio) else math.nan
            if not ci_excludes_one:
                verdict = "no detectable difference"
            elif effect < args.min_effect:
                verdict = "practically negligible"
            else:
                higher = ratio > 1
                better = higher if args.higher_is_better else not higher
                verdict = "better" if better else "worse"
            notes = []
            if min(len(vals), len(base)) < 5:
                notes.append("n<5: CI/p unreliable")
            if ci_excludes_one and p >= args.alpha:
                notes.append("CI and rank test disagree")
            rows.append({
                "scenario": scenario, "impl": impl, "baseline": args.baseline, "metric": args.metric,
                "n_impl": len(vals), "n_base": len(base), "median_impl": mi, "median_base": mb,
                "diff": diff, "diff_ci_lo": d_lo, "diff_ci_hi": d_hi,
                "ratio": ratio, "ratio_ci_lo": r_lo, "ratio_ci_hi": r_hi,
                "mw_p": p, "mw_method": method, "cliffs_delta": delta, "cliffs_magnitude": cliffs_label(delta),
                "verdict": verdict, "notes": "; ".join(notes),
            })

    cols = ["scenario", "impl", "baseline", "metric", "n_impl", "n_base", "median_impl", "median_base", "diff",
            "diff_ci_lo", "diff_ci_hi", "ratio", "ratio_ci_lo", "ratio_ci_hi", "mw_p", "mw_method",
            "cliffs_delta", "cliffs_magnitude", "verdict", "notes"]
    direction = "higher is better" if args.higher_is_better else "lower is better"
    print(f"# {args.metric} vs {args.baseline} ({direction}; practical threshold {args.min_effect:.0%}; "
          f"95% bootstrap CI over runs)")
    print_table(rows, ["scenario", "impl", "median_impl", "median_base", "ratio", "ratio_ci_lo", "ratio_ci_hi",
                       "mw_p", "cliffs_delta", "cliffs_magnitude", "verdict", "notes"])
    if args.out:
        write_csv(Path(args.out), rows, cols)
        print(f"\nwrote {args.out}")


# ----------------------------------------------------------------------------- CLI

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog="Methodology and examples: see the docstring at the top of scripts/stats.py.")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("plan-order", help="blocked randomised run order")
    a.add_argument("--impls", required=True)
    a.add_argument("--scenarios", required=True)
    a.add_argument("--runs", type=int, default=5)
    a.add_argument("--seed", type=int, required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--force", action="store_true")
    a.set_defaults(func=cmd_plan_order)

    b = sub.add_parser("steady-state", help="end of warmup: MSER-5 truncation + rolling CoV check")
    b.add_argument("--input", required=True, help="CSV file, plain or .gz")
    b.add_argument("--time-col", required=True)
    b.add_argument("--value-col", required=True)
    b.add_argument("--window", type=int, default=6, help="points per window")
    b.add_argument("--cov", type=float, default=0.05, help="CoV threshold")
    b.add_argument("--consecutive", type=int, default=3, help="windows in a row below threshold")
    b.add_argument("--batch", type=int, default=5, help="MSER batch size (MSER-5 by default)")
    b.add_argument("--json")
    b.set_defaults(func=cmd_steady_state)

    c = sub.add_parser("summarize", help="per-run and per-group latency statistics")
    c.add_argument("--input", required=True, nargs="+",
                   help="one or more CSV files, plain or .gz (e.g. results/raw-samples/*.k6.csv.gz)")
    c.add_argument("--format", choices=["k6", "long"], default="k6")
    c.add_argument("--metric", default="http_req_duration", help="k6 metric_name to use (k6 format)")
    c.add_argument("--group", default="impl,scenario,run",
                   help="grouping keys (fixed: impl,scenario,run; from testid tag or explicit columns)")
    c.add_argument("--only-ok", action="store_true", help="k6: keep only expected_response=true samples")
    c.add_argument("--skip-seconds", type=float, default=0, help="drop the first N seconds of each run (warmup)")
    c.add_argument("--resamples", type=int, default=10000)
    c.add_argument("--seed", type=int, default=1)
    c.add_argument("--out", help="runs CSV; groups go to <stem>.groups.csv next to it")
    c.add_argument("--json")
    c.set_defaults(func=cmd_summarize)

    d = sub.add_parser("compare", help="each impl vs baseline on a run-level metric")
    d.add_argument("--summary", required=True, help="runs CSV produced by `summarize`")
    d.add_argument("--baseline", default="before")
    d.add_argument("--metric", default="p99")
    d.add_argument("--min-effect", type=float, default=0.05, help="smallest relative change that matters")
    d.add_argument("--higher-is-better", action="store_true")
    d.add_argument("--alpha", type=float, default=0.05)
    d.add_argument("--resamples", type=int, default=10000)
    d.add_argument("--seed", type=int, default=1)
    d.add_argument("--out")
    d.set_defaults(func=cmd_compare)

    args = p.parse_args(argv)
    if getattr(args, "group", "impl,scenario,run") != "impl,scenario,run":
        sys.exit("error: only --group impl,scenario,run is supported")
    args.func(args)


if __name__ == "__main__":
    main()
