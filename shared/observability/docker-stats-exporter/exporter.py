"""Per-container resource metrics from the Docker Engine API, in Prometheus text format.

Why not cAdvisor: on Docker Desktop / WSL2 cAdvisor cannot discover containers (it only reports "/"),
so it is useless for the lab's main platform. The Engine API is what `docker stats` uses and works
everywhere Docker runs.

Only containers attached to LAB_NETWORK are reported (topic stacks + the observability stack itself,
so its own overhead is visible). Counters are exported raw; compute rates in PromQL.
Standard library only.
"""

import http.client
import json
import os
import socket
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DOCKER_SOCK = os.environ.get("DOCKER_SOCK", "/var/run/docker.sock")
LAB_NETWORK = os.environ.get("LAB_NETWORK", "backend-lab")
INTERVAL = float(os.environ.get("COLLECT_INTERVAL_SECONDS", "5"))
PORT = int(os.environ.get("PORT", "9417"))


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout=10):
        super().__init__("localhost", timeout=timeout)
        self._path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._path)


def docker_get(path):
    conn = UnixHTTPConnection(DOCKER_SOCK)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        if resp.status != 200:
            raise RuntimeError(f"GET {path} -> {resp.status}: {body[:200]!r}")
        return json.loads(body)
    finally:
        conn.close()


def esc(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# name, type, help
METRICS = [
    ("lab_container_cpu_usage_seconds_total", "counter", "Cumulative CPU time consumed by the container."),
    ("lab_container_cpu_limit_cores", "gauge", "CPU limit in cores (0 = unlimited)."),
    ("lab_container_cpu_throttled_periods_total", "counter", "CFS periods in which the container was throttled."),
    ("lab_container_cpu_periods_total", "counter", "CFS enforcement periods elapsed."),
    ("lab_container_cpu_throttled_seconds_total", "counter", "Total time the container was throttled."),
    ("lab_container_memory_usage_bytes", "gauge", "Memory usage excluding inactive page cache (same as `docker stats`)."),
    ("lab_container_memory_limit_bytes", "gauge", "Memory limit (host total when unlimited)."),
    ("lab_container_network_receive_bytes_total", "counter", "Bytes received on all interfaces."),
    ("lab_container_network_transmit_bytes_total", "counter", "Bytes transmitted on all interfaces."),
    ("lab_container_blkio_read_bytes_total", "counter", "Bytes read from block devices."),
    ("lab_container_blkio_write_bytes_total", "counter", "Bytes written to block devices."),
    ("lab_container_pids", "gauge", "Number of processes/threads in the container."),
    ("lab_container_restart_count", "gauge", "Times Docker restarted the container."),
    ("lab_container_oom_killed", "gauge", "1 if the last exit was an OOM kill."),
]


def container_samples(summary):
    cid = summary["Id"]
    stats = docker_get(f"/containers/{cid}/stats?stream=false&one-shot=true")
    inspect = docker_get(f"/containers/{cid}/json")
    labels_raw = summary.get("Labels") or {}
    labels = {
        "container": summary["Names"][0].lstrip("/"),
        "compose_project": labels_raw.get("com.docker.compose.project", ""),
        "compose_service": labels_raw.get("com.docker.compose.service", ""),
    }

    cpu = stats.get("cpu_stats", {})
    throttling = cpu.get("throttling_data", {})
    mem = stats.get("memory_stats", {})
    mem_stats = mem.get("stats", {})
    # docker stats subtracts reclaimable cache: cgroup v1 total_inactive_file, v2 inactive_file
    cache = mem_stats.get("total_inactive_file", mem_stats.get("inactive_file", 0))
    nets = stats.get("networks") or {}
    blkio = (stats.get("blkio_stats") or {}).get("io_service_bytes_recursive") or []
    host_cfg = inspect.get("HostConfig", {})
    nano_cpus = host_cfg.get("NanoCpus") or 0
    quota, period = host_cfg.get("CpuQuota") or 0, host_cfg.get("CpuPeriod") or 0
    cpu_limit = nano_cpus / 1e9 if nano_cpus else (quota / period if quota > 0 and period > 0 else 0)
    state = inspect.get("State", {})

    values = {
        "lab_container_cpu_usage_seconds_total": cpu.get("cpu_usage", {}).get("total_usage", 0) / 1e9,
        "lab_container_cpu_limit_cores": cpu_limit,
        "lab_container_cpu_throttled_periods_total": throttling.get("throttled_periods", 0),
        "lab_container_cpu_periods_total": throttling.get("periods", 0),
        "lab_container_cpu_throttled_seconds_total": throttling.get("throttled_time", 0) / 1e9,
        "lab_container_memory_usage_bytes": max(mem.get("usage", 0) - cache, 0),
        "lab_container_memory_limit_bytes": mem.get("limit", 0),
        "lab_container_network_receive_bytes_total": sum(n.get("rx_bytes", 0) for n in nets.values()),
        "lab_container_network_transmit_bytes_total": sum(n.get("tx_bytes", 0) for n in nets.values()),
        "lab_container_blkio_read_bytes_total": sum(e.get("value", 0) for e in blkio if e.get("op", "").lower() == "read"),
        "lab_container_blkio_write_bytes_total": sum(e.get("value", 0) for e in blkio if e.get("op", "").lower() == "write"),
        "lab_container_pids": (stats.get("pids_stats") or {}).get("current", 0),
        "lab_container_restart_count": inspect.get("RestartCount", 0),
        "lab_container_oom_killed": 1 if state.get("OOMKilled") else 0,
    }
    return labels, values


class Collector:
    def __init__(self):
        self._lock = threading.Lock()
        self._text = "# no data collected yet\n"
        self._pool = ThreadPoolExecutor(max_workers=8)

    def collect_once(self):
        started = time.monotonic()
        filters = json.dumps({"network": [LAB_NETWORK], "status": ["running"]})
        summaries = docker_get("/containers/json?filters=" + urllib.parse.quote(filters))
        results, errors = [], 0
        for fut in [self._pool.submit(container_samples, s) for s in summaries]:
            try:
                results.append(fut.result(timeout=15))
            except Exception as exc:  # container vanished mid-scrape, API hiccup...
                errors += 1
                print(f"[docker-stats-exporter] {exc}", flush=True)

        lines = []
        for name, mtype, help_text in METRICS:
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} {mtype}")
            for labels, values in results:
                label_str = ",".join(f'{k}="{esc(v)}"' for k, v in labels.items())
                lines.append(f"{name}{{{label_str}}} {values[name]}")
        lines.append("# HELP lab_docker_stats_collect_seconds Duration of the last collection loop.")
        lines.append("# TYPE lab_docker_stats_collect_seconds gauge")
        lines.append(f"lab_docker_stats_collect_seconds {time.monotonic() - started:.3f}")
        lines.append("# HELP lab_docker_stats_errors Containers that failed in the last collection loop.")
        lines.append("# TYPE lab_docker_stats_errors gauge")
        lines.append(f"lab_docker_stats_errors {errors}")
        with self._lock:
            self._text = "\n".join(lines) + "\n"

    def run(self):
        while True:
            try:
                self.collect_once()
            except Exception as exc:
                print(f"[docker-stats-exporter] collection failed: {exc}", flush=True)
            time.sleep(INTERVAL)

    def text(self):
        with self._lock:
            return self._text


COLLECTOR = Collector()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        body = COLLECTOR.text().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=COLLECTOR.run, daemon=True).start()
    print(f"[docker-stats-exporter] listening on :{PORT}, network={LAB_NETWORK}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
