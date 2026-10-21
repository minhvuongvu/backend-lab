"""Fault injection on the app -> postgres link through Toxiproxy's HTTP API (stdlib only).

Usage (from experiments/):
  python3 chaos/toxiproxy.py latency --ms 200 --jitter 50       # add latency downstream
  python3 chaos/toxiproxy.py timeout --ms 0                      # stall: data stops flowing (gray failure)
  python3 chaos/toxiproxy.py partition                           # disable the proxy: connections refused/reset
  python3 chaos/toxiproxy.py bandwidth --kbps 64
  python3 chaos/toxiproxy.py reset-peer --ms 1000                # TCP RST after a delay
  python3 chaos/toxiproxy.py clear                               # remove all toxics, re-enable the proxy
  python3 chaos/toxiproxy.py status

Why Toxiproxy instead of `tc netem`: it works the same on Docker Desktop (Windows/macOS) where
the VM kernel and container capabilities make tc unreliable, and it targets one link only.
Every injection prints a JSON line with a UTC timestamp so it can be aligned with k6/Prometheus data;
redirect it into results/raw/<id>-chaos.jsonl.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

# Same port variable as docker-compose.yml (override when 8474 is taken on this machine).
API = f"http://localhost:{os.environ.get('TOXIPROXY_API_PORT', '8474')}"
PROXY = "postgres"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        sys.exit(f"toxiproxy {method} {path} -> {exc.code}: {exc.read().decode(errors='replace')}")
    except urllib.error.URLError as exc:
        sys.exit(f"toxiproxy API not reachable at {API}: {exc.reason} (is `make up` running?)")


def add_toxic(name, kind, attributes, stream="downstream"):
    return call("POST", f"/proxies/{PROXY}/toxics",
                {"name": name, "type": kind, "stream": stream, "toxicity": 1.0, "attributes": attributes})


def log(action, **fields):
    print(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "proxy": PROXY, "action": action, **fields}))


def main():
    global API, PROXY
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api", default=API)
    p.add_argument("--proxy", default=PROXY)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("latency"); s.add_argument("--ms", type=int, required=True); s.add_argument("--jitter", type=int, default=0)
    s = sub.add_parser("timeout"); s.add_argument("--ms", type=int, default=0)
    s = sub.add_parser("bandwidth"); s.add_argument("--kbps", type=int, required=True)
    s = sub.add_parser("reset-peer"); s.add_argument("--ms", type=int, default=0)
    sub.add_parser("partition")
    sub.add_parser("clear")
    sub.add_parser("status")
    a = p.parse_args()
    API, PROXY = a.api, a.proxy

    if a.cmd == "latency":
        add_toxic("latency", "latency", {"latency": a.ms, "jitter": a.jitter}); log("latency", ms=a.ms, jitter=a.jitter)
    elif a.cmd == "timeout":
        add_toxic("timeout", "timeout", {"timeout": a.ms}); log("timeout", ms=a.ms)
    elif a.cmd == "bandwidth":
        add_toxic("bandwidth", "bandwidth", {"rate": a.kbps}); log("bandwidth", kbps=a.kbps)
    elif a.cmd == "reset-peer":
        add_toxic("reset_peer", "reset_peer", {"timeout": a.ms}); log("reset-peer", ms=a.ms)
    elif a.cmd == "partition":
        call("POST", f"/proxies/{PROXY}", {"enabled": False}); log("partition")
    elif a.cmd == "clear":
        for t in call("GET", f"/proxies/{PROXY}/toxics") or []:
            call("DELETE", f"/proxies/{PROXY}/toxics/{t['name']}")
        call("POST", f"/proxies/{PROXY}", {"enabled": True}); log("clear")
    elif a.cmd == "status":
        print(json.dumps({"proxy": call("GET", f"/proxies/{PROXY}"), "toxics": call("GET", f"/proxies/{PROXY}/toxics")}, indent=2))


if __name__ == "__main__":
    main()
