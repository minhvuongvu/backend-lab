#!/usr/bin/env bash
# Container-level faults for the experiment stack. Prints a JSON line with a UTC timestamp per action
# (append to results/raw/<id>-chaos.jsonl to align with k6/Prometheus).
#   chaos/container.sh kill app            # SIGKILL: crash without graceful shutdown
#   chaos/container.sh stop app            # SIGTERM then SIGKILL after the grace period (rolling-restart-like)
#   chaos/container.sh restart app
#   chaos/container.sh pause postgres 10   # freeze all processes for N seconds (GC-pause / VM-stall-like)
set -euo pipefail

action="${1:?action: kill|stop|restart|pause}"
service="${2:?service name from docker-compose.yml}"
seconds="${3:-10}"

log() { printf '{"ts":"%s","action":"%s","service":"%s"%s}\n' "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" "$1" "$service" "${2:-}"; }

case "$action" in
  kill)    docker compose kill -s SIGKILL "$service" >/dev/null; log kill ;;
  stop)    docker compose stop "$service" >/dev/null; log stop ;;
  restart) docker compose restart "$service" >/dev/null; log restart ;;
  pause)   docker compose pause "$service" >/dev/null; log pause ",\"seconds\":$seconds"
           sleep "$seconds"
           docker compose unpause "$service" >/dev/null; log unpause ;;
  *) echo "unknown action: $action" >&2; exit 2 ;;
esac
