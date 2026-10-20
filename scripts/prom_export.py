#!/usr/bin/env python3
"""Export Prometheus range queries to CSV so experiment numbers can live in results/raw/.

CLAUDE.md requires every number in 05-results / 06-conclusion to point at a file in results/raw/.
Dashboards are not evidence; this script turns what Prometheus saw during a run into a raw file.
Standard library only.

Output is "long" CSV, one row per (query, series, timestamp):
    query, timestamp (RFC3339 UTC), unix_ts, value, <label columns, sorted>
which pivots easily in pandas:
    df = pd.read_csv(path); df.pivot_table(index="unix_ts", columns=["query", "container"], values="value")
NaN / +Inf / -Inf are kept as the strings Prometheus returns.

Typical use around a k6 run (from topics/<slug>/):
    START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    k6 run ...
    END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    python3 ../../scripts/prom_export.py --start $START --end $END \\
        --preset resources --label compose_project=<topic> \\
        --out results/raw/<impl>-<scenario>-<run>-<ts>-resources.csv --meta

More examples:
    # last 15 minutes, several presets in one file
    python3 scripts/prom_export.py --start -15m --end now --preset postgres --preset kafka \\
        --label compose_project=outbox --out results/raw/a-s1-1-20261020T1200-datastores.csv
    # ad-hoc query (repeatable); NAME is what appears in the `query` column
    python3 scripts/prom_export.py --start 1760961600 --end 1760962200 --step 1s \\
        --query 'outbox_lag=max(outbox_pending_events)' --out /tmp/lag.csv

Placeholders inside preset queries:
    __SEL__    replaced by the --label matchers (k="v",...) or removed when no --label is given
    __RANGE__  rate() window: max(30s, 4 x step) so rates stay defined at coarse steps
Exit codes: 0 ok, 1 bad arguments / refused overwrite, 2 Prometheus HTTP or PromQL error.
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DEFAULT_PROM = os.environ.get("PROM_URL", "http://localhost:9090")

PRESETS = {
    # Per-container resources from shared/observability/docker-stats-exporter (lab_container_*).
    "resources": {
        "cpu_cores": "sum by (container, compose_project, compose_service) (rate(lab_container_cpu_usage_seconds_total{__SEL__}[__RANGE__]))",
        "cpu_limit_cores": "max by (container, compose_project, compose_service) (lab_container_cpu_limit_cores{__SEL__})",
        "cpu_throttled_ratio": "sum by (container, compose_project, compose_service) (rate(lab_container_cpu_throttled_periods_total{__SEL__}[__RANGE__])) / clamp_min(sum by (container, compose_project, compose_service) (rate(lab_container_cpu_periods_total{__SEL__}[__RANGE__])), 1e-9)",
        "memory_bytes": "max by (container, compose_project, compose_service) (lab_container_memory_usage_bytes{__SEL__})",
        "net_rx_bytes_per_s": "sum by (container, compose_project, compose_service) (rate(lab_container_network_receive_bytes_total{__SEL__}[__RANGE__]))",
        "net_tx_bytes_per_s": "sum by (container, compose_project, compose_service) (rate(lab_container_network_transmit_bytes_total{__SEL__}[__RANGE__]))",
        "blkio_read_bytes_per_s": "sum by (container, compose_project, compose_service) (rate(lab_container_blkio_read_bytes_total{__SEL__}[__RANGE__]))",
        "blkio_write_bytes_per_s": "sum by (container, compose_project, compose_service) (rate(lab_container_blkio_write_bytes_total{__SEL__}[__RANGE__]))",
    },
    # Spring Boot / Micrometer JVM metrics.
    "jvm": {
        "process_cpu_usage": "process_cpu_usage{__SEL__}",
        "heap_used_bytes": "sum by (instance, job) (jvm_memory_used_bytes{area=\"heap\",__SEL__})",
        "gc_pause_seconds_per_s": "sum by (instance, job, gc) (rate(jvm_gc_pause_seconds_sum{__SEL__}[__RANGE__]))",
        "hikari_active": "hikaricp_connections_active{__SEL__}",
        "hikari_pending": "hikaricp_connections_pending{__SEL__}",
    },
    # Spring Boot HTTP server metrics (percentiles need percentiles-histogram=true).
    "http": {
        "req_per_s": "sum by (instance, uri) (rate(http_server_requests_seconds_count{uri!~\"/actuator.*\",__SEL__}[__RANGE__]))",
        "error_ratio": "sum by (instance, uri) (rate(http_server_requests_seconds_count{uri!~\"/actuator.*\",status=~\"5..\",__SEL__}[__RANGE__])) / clamp_min(sum by (instance, uri) (rate(http_server_requests_seconds_count{uri!~\"/actuator.*\",__SEL__}[__RANGE__])), 1e-9)",
        "p50_seconds": "histogram_quantile(0.50, sum by (le, instance, uri) (rate(http_server_requests_seconds_bucket{uri!~\"/actuator.*\",__SEL__}[__RANGE__])))",
        "p95_seconds": "histogram_quantile(0.95, sum by (le, instance, uri) (rate(http_server_requests_seconds_bucket{uri!~\"/actuator.*\",__SEL__}[__RANGE__])))",
        "p99_seconds": "histogram_quantile(0.99, sum by (le, instance, uri) (rate(http_server_requests_seconds_bucket{uri!~\"/actuator.*\",__SEL__}[__RANGE__])))",
    },
    # k6 via remote write (K6_PROMETHEUS_RW_TREND_STATS="p(50),p(95),p(99),...").
    "k6": {
        "req_per_s": "sum by (testid) (rate(k6_http_reqs_total{__SEL__}[__RANGE__]))",
        "failed_req_per_s": "sum by (testid) (rate(k6_http_reqs_total{expected_response=\"false\",__SEL__}[__RANGE__]))",
        "duration_p50_seconds": "max by (testid) (k6_http_req_duration_p50{__SEL__})",
        "duration_p95_seconds": "max by (testid) (k6_http_req_duration_p95{__SEL__})",
        "duration_p99_seconds": "max by (testid) (k6_http_req_duration_p99{__SEL__})",
        "vus": "sum by (testid) (k6_vus{__SEL__})",
    },
    # postgres-exporter (shared/observability/exporters/postgres.yml).
    "postgres": {
        "up": "pg_up{__SEL__}",
        "backends": "sum by (instance, datname) (pg_stat_database_numbackends{datname!~\"template.*\",__SEL__})",
        "commits_per_s": "sum by (instance, datname) (rate(pg_stat_database_xact_commit{datname!~\"template.*\",__SEL__}[__RANGE__]))",
        "rollbacks_per_s": "sum by (instance, datname) (rate(pg_stat_database_xact_rollback{datname!~\"template.*\",__SEL__}[__RANGE__]))",
        "cache_hit_ratio": "sum by (instance, datname) (rate(pg_stat_database_blks_hit{datname!~\"template.*\",__SEL__}[__RANGE__])) / clamp_min(sum by (instance, datname) (rate(pg_stat_database_blks_hit{datname!~\"template.*\",__SEL__}[__RANGE__])) + sum by (instance, datname) (rate(pg_stat_database_blks_read{datname!~\"template.*\",__SEL__}[__RANGE__])), 1e-9)",
        "deadlocks_per_s": "sum by (instance, datname) (rate(pg_stat_database_deadlocks{datname!~\"template.*\",__SEL__}[__RANGE__]))",
        "locks": "sum by (instance, mode) (pg_locks_count{__SEL__})",
        "tup_inserted_per_s": "sum by (instance, datname) (rate(pg_stat_database_tup_inserted{datname!~\"template.*\",__SEL__}[__RANGE__]))",
        "max_tx_duration_seconds": "max by (instance) (pg_stat_activity_max_tx_duration{__SEL__})",
    },
    # redis_exporter (shared/observability/exporters/redis.yml).
    "redis": {
        "up": "redis_up{__SEL__}",
        "commands_per_s": "sum by (instance) (rate(redis_commands_processed_total{__SEL__}[__RANGE__]))",
        "connected_clients": "redis_connected_clients{__SEL__}",
        "memory_used_bytes": "redis_memory_used_bytes{__SEL__}",
        "hit_ratio": "sum by (instance) (rate(redis_keyspace_hits_total{__SEL__}[__RANGE__])) / clamp_min(sum by (instance) (rate(redis_keyspace_hits_total{__SEL__}[__RANGE__])) + sum by (instance) (rate(redis_keyspace_misses_total{__SEL__}[__RANGE__])), 1e-9)",
        "evicted_keys_per_s": "sum by (instance) (rate(redis_evicted_keys_total{__SEL__}[__RANGE__]))",
    },
    # kafka-exporter (shared/observability/exporters/kafka.yml). Lag/offset series exist only once topics/groups exist.
    "kafka": {
        "brokers": "kafka_brokers{__SEL__}",
        "consumergroup_lag": "sum by (consumergroup, topic) (kafka_consumergroup_lag{__SEL__})",
        "produce_msgs_per_s": "sum by (topic) (rate(kafka_topic_partition_current_offset{__SEL__}[__RANGE__]))",
        "consume_msgs_per_s": "sum by (consumergroup, topic) (rate(kafka_consumergroup_current_offset{__SEL__}[__RANGE__]))",
    },
}

DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)(ms|s|m|h|d|w)$")
UNIT_SECONDS = {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


class ExportError(Exception):
    """Prometheus returned an HTTP or PromQL error (exit code 2)."""


def parse_duration(text):
    m = DURATION_RE.match(text.strip())
    if not m:
        raise argparse.ArgumentTypeError(f"invalid duration {text!r} (expected e.g. 500ms, 5s, 15m, 1h)")
    return float(m.group(1)) * UNIT_SECONDS[m.group(2)]


def parse_time(text, now):
    """RFC3339, unix seconds, 'now', or relative '-15m'."""
    t = text.strip()
    if t == "now":
        return now
    if t.startswith("-"):
        return now - parse_duration(t[1:])
    try:
        return float(t)
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid time {text!r} (RFC3339, unix seconds, 'now' or '-15m')")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def fmt_duration(seconds):
    if seconds >= 1 and float(seconds).is_integer():
        return f"{int(seconds)}s"
    return f"{int(round(seconds * 1000))}ms"


def rfc3339(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_selector(labels):
    parts = []
    for item in labels:
        if "=" not in item:
            raise argparse.ArgumentTypeError(f"--label expects key=value, got {item!r}")
        key, value = item.split("=", 1)
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
            raise argparse.ArgumentTypeError(f"invalid label name {key!r}")
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'{key}="{escaped}"')
    return ",".join(parts)


def render(template, selector, rate_range):
    q = template.replace(",__SEL__", f",{selector}" if selector else "")
    q = q.replace("__SEL__", selector)
    return q.replace("__RANGE__", rate_range)


def query_range(prom, promql, start, end, step):
    params = urllib.parse.urlencode({"query": promql, "start": f"{start:.3f}", "end": f"{end:.3f}", "step": fmt_duration(step)})
    url = prom.rstrip("/") + "/api/v1/query_range"
    req = urllib.request.Request(url, data=params.encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        try:
            detail = json.loads(detail).get("error", detail)
        except ValueError:
            pass
        raise ExportError(f"HTTP {exc.code} from {url}: {detail}") from None
    except urllib.error.URLError as exc:
        raise ExportError(f"cannot reach Prometheus at {prom}: {exc.reason}") from None
    if body.get("status") != "success":
        raise ExportError(f"{body.get('errorType', 'error')}: {body.get('error', body)}")
    for warning in body.get("warnings", []) or []:
        print(f"  warning from Prometheus: {warning}", file=sys.stderr)
    return body["data"]["result"]


class Parser(argparse.ArgumentParser):
    """Usage errors exit with 1 so that 2 always means "Prometheus/PromQL error"."""

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def normalise_argv(argv):
    """Allow `--start -15m` (argparse would read -15m as an option)."""
    out, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a in ("--start", "--end") and i + 1 < len(argv) and re.match(r"^-\d", argv[i + 1]):
            out.append(f"{a}={argv[i + 1]}")
            i += 2
            continue
        out.append(a)
        i += 1
    return out


def main(argv=None):
    parser = Parser(
        description="Export Prometheus range queries to long-format CSV for results/raw/.",
        epilog="Presets: " + ", ".join(sorted(PRESETS)),
    )
    parser.add_argument("--prom", default=DEFAULT_PROM, help=f"Prometheus base URL (default: $PROM_URL or {DEFAULT_PROM})")
    parser.add_argument("--start", required=True, help="RFC3339, unix seconds, 'now' or relative like -15m")
    parser.add_argument("--end", default="now", help="same formats as --start (default: now)")
    parser.add_argument("--step", default="5s", type=parse_duration, help="resolution, e.g. 1s, 5s (default 5s)")
    parser.add_argument("--query", action="append", default=[], metavar="NAME=PROMQL", help="ad-hoc query (repeatable)")
    parser.add_argument("--preset", action="append", default=[], choices=sorted(PRESETS), help="named query set (repeatable)")
    parser.add_argument("--label", action="append", default=[], metavar="KEY=VALUE", help="matcher injected into preset queries (repeatable)")
    parser.add_argument("--out", required=True, help="CSV output path (parent dirs are created)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing file (raw data should not be rewritten)")
    parser.add_argument("--meta", action="store_true", help="also write <out>.meta.json describing the export")
    args = parser.parse_args(normalise_argv(sys.argv[1:] if argv is None else argv))

    now = datetime.now(tz=timezone.utc).timestamp()
    try:
        start, end = parse_time(args.start, now), parse_time(args.end, now)
        selector = build_selector(args.label)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    if end <= start:
        parser.error(f"--end ({rfc3339(end)}) must be after --start ({rfc3339(start)})")
    if (end - start) / args.step > 11000:
        parser.error("too many points per series (Prometheus limit 11000): increase --step or shorten the range")

    rate_range = fmt_duration(max(30.0, 4 * args.step))
    queries = {}
    for preset in args.preset:
        for name, template in PRESETS[preset].items():
            queries[f"{preset}.{name}"] = render(template, selector, rate_range)
    for item in args.query:
        if "=" not in item:
            parser.error(f"--query expects NAME=PROMQL, got {item!r}")
        name, promql = item.split("=", 1)
        queries[name.strip()] = promql.strip()
    if not queries:
        parser.error("nothing to export: give at least one --preset or --query")

    if os.path.exists(args.out) and not args.force:
        print(f"refusing to overwrite {args.out}: raw data must not be rewritten (use --force if this is intended)", file=sys.stderr)
        return 1

    print(f"Prometheus {args.prom} | {rfc3339(start)} -> {rfc3339(end)} | step {fmt_duration(args.step)} | rate window {rate_range}")
    rows, label_keys, empty, summary = [], set(), [], {}
    try:
        for name, promql in queries.items():
            result = query_range(args.prom, promql, start, end, args.step)
            points = 0
            for series in result:
                metric = {k: v for k, v in series.get("metric", {}).items()}
                label_keys.update(metric)
                for ts, value in series.get("values", []):
                    rows.append((name, float(ts), value, metric))
                    points += 1
            summary[name] = {"series": len(result), "points": points}
            flag = "  <-- no series" if not result else ""
            print(f"  {name:45s} series={len(result):<4d} points={points}{flag}")
            if not result:
                empty.append(name)
    except ExportError as exc:
        print(f"error in query {name!r}: {exc}\n  promql: {promql}", file=sys.stderr)
        return 2

    keys = sorted(label_keys)
    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["query", "timestamp", "unix_ts", "value", *keys])
        for name, ts, value, metric in rows:
            writer.writerow([name, rfc3339(ts), f"{ts:.3f}", value, *(metric.get(k, "") for k in keys)])

    if args.meta:
        meta = {
            "prometheus": args.prom,
            "start": rfc3339(start),
            "end": rfc3339(end),
            "start_unix": start,
            "end_unix": end,
            "step": fmt_duration(args.step),
            "rate_window": rate_range,
            "labels": args.label,
            "presets": args.preset,
            "queries": queries,
            "per_query": summary,
            "rows": len(rows),
            "label_columns": keys,
            "exported_at": rfc3339(now),
            "tool": "scripts/prom_export.py",
        }
        with open(args.out + ".meta.json", "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    print(f"wrote {len(rows)} rows to {args.out}" + (f" (+ {args.out}.meta.json)" if args.meta else ""))
    if empty:
        print(f"warning: {len(empty)} quer{'y' if len(empty) == 1 else 'ies'} returned no series: {', '.join(empty)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
