#!/usr/bin/env bash
# Check that this machine can run the lab. Usage: make doctor  (or: bash scripts/doctor.sh)
# Prints OK / WARN / FAIL per item; exits 1 if anything required is missing.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

fails=0
ok()   { printf '  \033[32mOK\033[0m    %s\n' "$*"; }
warn() { printf '  \033[33mWARN\033[0m  %s\n' "$*"; }
fail() { printf '  \033[31mFAIL\033[0m  %s\n' "$*"; fails=$((fails + 1)); }
have() { command -v "$1" >/dev/null 2>&1; }

echo "Tools"
have make && ok "make: $(make --version | head -1)" || fail "make not found (Windows: winget install ezwinports.make)"
ok "bash: ${BASH_VERSION}"
have git && ok "git: $(git --version)" || fail "git not found"

if have docker && docker info >/dev/null 2>&1; then
  ok "docker: server $(docker version --format '{{.Server.Version}}' 2>/dev/null)"
  docker compose version >/dev/null 2>&1 && ok "docker compose: $(docker compose version --short)" || fail "docker compose v2 missing"
else
  fail "docker not running (start Docker Desktop)"
fi

PY=""
for c in python3 python; do
  if have "$c" && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then PY="$c"; break; fi
done
[[ -n "$PY" ]] && ok "python: $($PY --version 2>&1) via '$PY'" || fail "Python >= 3.9 not found (on Windows 'python3' may be the Store alias)"
if [[ -n "$PY" ]]; then
  $PY -c 'import pandas, matplotlib' >/dev/null 2>&1 \
    && ok "pandas + matplotlib installed" \
    || warn "pandas/matplotlib missing locally — charts run in the analysis image (make analysis CMD=...)"
fi
if have docker; then
  docker image inspect backend-lab/analysis:1 >/dev/null 2>&1 \
    && ok "analysis image backend-lab/analysis:1 built" \
    || warn "analysis image not built yet — make analysis-image (also built on first make analysis)"
fi

JDK21=""
if have java && java -version 2>&1 | grep -q 'version "21'; then JDK21="java on PATH"; fi
[[ -z "$JDK21" && -n "${JAVA_HOME:-}" && -x "$JAVA_HOME/bin/java" ]] && "$JAVA_HOME/bin/java" -version 2>&1 | grep -q 'version "21' && JDK21="JAVA_HOME=$JAVA_HOME"
if [[ -z "$JDK21" ]]; then
  for d in "$HOME"/.jdks/*21* /c/Users/*/.jdks/*21* /usr/lib/jvm/*21*; do
    [[ -x "$d/bin/java" ]] && JDK21="$d (set JAVA_HOME to this for ./mvnw)" && break
  done
fi
[[ -n "$JDK21" ]] && ok "JDK 21: $JDK21" || fail "JDK 21 not found"

if have k6; then ok "k6: $(k6 version 2>/dev/null | head -1)"
elif have docker; then warn "k6 not on PATH — experiments can use the grafana/k6 docker image"
else fail "k6 not found"; fi

browser=""
for b in "/c/Program Files/Google/Chrome/Application/chrome.exe" "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" google-chrome chromium; do
  { [[ -x "$b" ]] || have "$b"; } && browser="$b" && break
done
[[ -n "$browser" ]] && ok "headless browser for render checks: $browser" || warn "no Chrome/Edge — make check skips render checks"

if [[ -f lab.env ]]; then
  set -a; . ./lab.env; set +a
  echo "Ports (lab.env loaded; edit it to move a port)"
else
  echo "Ports (lab defaults; to move one: cp lab.env.example lab.env and edit)"
fi
for spec in 9090:PROM_PORT 3000:GRAFANA_PORT 4317:OTLP_GRPC_PORT 4318:OTLP_HTTP_PORT 4040:PYROSCOPE_PORT 12345:ALLOY_PORT 8474:TOXIPROXY_API_PORT 5432:- 6379:- 9092:- 8080:-; do
  port=${spec%%:*}; var=${spec##*:}
  [[ "$var" != - && -n "${!var:-}" ]] && port=${!var}
  [[ "$var" == - ]] && var=""
  holder=""
  if have docker; then holder=$(docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -E "(:|\])$port->" | awk '{print $1}' | head -1); fi
  if [[ -n "$holder" ]]; then
    [[ "$holder" == backend-lab-obs-* ]] && ok "$port used by lab container $holder" || warn "$port taken by container '$holder'${var:+ — set $var=<free port> in lab.env}"
  elif (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
    warn "$port taken by a non-docker process${var:+ — set $var=<free port> in lab.env}"
  else
    ok "$port free"
  fi
done

echo "Lab state"
if have docker; then
  docker network inspect backend-lab >/dev/null 2>&1 && ok "docker network backend-lab exists" || warn "network backend-lab missing (make lab-network / make obs-up creates it)"
fi
if remote=$(git remote get-url origin 2>/dev/null); then
  # Never print credentials embedded in the URL (https://<token>@host/...).
  if [[ "$remote" =~ ^https?://[^/@]+@ ]]; then
    warn "git remote origin embeds credentials in the URL (${remote%%://*}://***@${remote#*@}) — revoke that token and use a credential manager"
  else
    ok "git remote origin: $remote"
  fi
else
  warn "no git remote 'origin' (no off-machine backup)"
fi
[[ -x .git/hooks/pre-commit ]] && ok "pre-commit hook installed" || warn "pre-commit hook not installed (make hooks)"

echo "Network (TLS interception was seen on this machine)"
for url in https://repo.maven.apache.org/maven2/ https://registry-1.docker.io/v2/ https://pypi.org/simple/; do
  if curl -s -o /dev/null -m 10 "$url" 2>/dev/null; then ok "TLS ok: $url"; else warn "TLS/network fails for $url (curl/pip may be blocked; Maven/Docker use their own trust stores)"; fi
done

echo
if (( fails > 0 )); then echo "$fails required item(s) missing."; exit 1; fi
echo "Ready."
