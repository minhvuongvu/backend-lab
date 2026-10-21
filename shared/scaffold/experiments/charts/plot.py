"""Charts for 05-results.html from stats.py output and raw k6 samples (pandas + matplotlib).

  python3 charts/plot.py cdf    --k6 ../results/analysis/k6-all.csv --scenario S1 --out ../results/charts/S1-latency-cdf.png
  python3 charts/plot.py ci-bar --groups ../results/analysis/runs.groups.csv --metric p99 --out ../results/charts/p99-ci.png
  python3 charts/plot.py sweep  --runs ../results/analysis/sweep-steps.csv --out ../results/charts/throughput-latency.png

Why these three: the CDF shows the whole latency distribution (tails included) instead of a few
percentiles; the CI bar shows whether before-vs-implementation differences exceed run-to-run variation;
the throughput-latency curve shows where each implementation saturates (the knee).
"""

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def split_testid(series):
    parts = series.str.rsplit("-", n=2, expand=True)
    return parts[0], parts[1], parts[2]


def cdf(args):
    # k6 CSV: built-in tags are columns (`scenario` = k6 scenario name: warmup/measure/...); custom tags such
    # as testid live in `extra_tags` ("testid=before-S1-1&phase=measure").
    wanted = {"metric_name", "metric_value", "scenario", "extra_tags", "testid"}
    df = pd.read_csv(args.k6, usecols=lambda c: c in wanted, dtype=str)
    df = df[df.metric_name == "http_req_duration"]
    df["metric_value"] = df.metric_value.astype(float)
    if "scenario" in df.columns:
        df = df[df.scenario != "warmup"]
    testid = df["testid"] if "testid" in df.columns else df.extra_tags.str.extract(r"(?:^|&)testid=([^&]+)")[0]
    df["impl"], df["k6_scenario"], df["run"] = split_testid(testid.fillna("unknown-unknown-0"))
    df = df[df.k6_scenario == args.scenario]
    if df.empty:
        raise SystemExit(f"no http_req_duration samples for scenario {args.scenario}")
    fig, ax = plt.subplots(figsize=(8, 5))
    for impl, g in df.groupby("impl"):
        v = np.sort(g.metric_value.to_numpy())
        ax.plot(v, np.arange(1, len(v) + 1) / len(v), label=f"{impl} (n={len(v)})")
    ax.set_xscale("log")
    ax.set_xlabel("latency (ms, log scale)")
    ax.set_ylabel("fraction of requests <= x")
    ax.set_title(f"Latency CDF - {args.scenario} (pooled runs, warmup excluded)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)


def ci_bar(args):
    g = pd.read_csv(args.groups)
    med, lo, hi = f"{args.metric}_median", f"{args.metric}_ci_lo", f"{args.metric}_ci_hi"
    missing = [c for c in (med, lo, hi) if c not in g.columns]
    if missing:
        raise SystemExit(f"columns {missing} not in {args.groups}; columns are {list(g.columns)}")
    g = g.sort_values(["scenario", "impl"])
    labels = g.scenario + " / " + g.impl
    fig, ax = plt.subplots(figsize=(max(6, len(g) * 0.9), 5))
    ax.bar(labels, g[med], yerr=[g[med] - g[lo], g[hi] - g[med]], capsize=4)
    ax.set_ylabel(f"{args.metric} (median of runs, 95% CI)")
    ax.set_title(f"{args.metric} by implementation (cluster-bootstrap CI over runs)")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)


def sweep(args):
    # expects columns: impl, offered_rate, throughput, p99 (one row per step and impl)
    d = pd.read_csv(args.runs)
    fig, ax = plt.subplots(figsize=(8, 5))
    for impl, g in d.groupby("impl"):
        g = g.sort_values("offered_rate")
        ax.plot(g.throughput, g.p99, marker="o", label=impl)
    ax.set_xlabel("achieved throughput (req/s)")
    ax.set_ylabel("p99 latency (ms)")
    ax.set_title("Throughput-latency curve (load sweep)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("cdf")
    s.add_argument("--k6", required=True)
    s.add_argument("--scenario", required=True)
    s.add_argument("--out", required=True)
    s = sub.add_parser("ci-bar")
    s.add_argument("--groups", required=True)
    s.add_argument("--metric", default="p99")
    s.add_argument("--out", required=True)
    s = sub.add_parser("sweep")
    s.add_argument("--runs", required=True)
    s.add_argument("--out", required=True)
    a = p.parse_args()
    {"cdf": cdf, "ci-bar": ci_bar, "sweep": sweep}[a.cmd](a)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
