# Experiment runner for topic {{SLUG}} (run from topics/{{SLUG}}/experiments).
# Every number in 05/06 must come from files these targets write (never edited by hand):
#   ../results/raw/          small, analysis-ready, committed (k6 summary JSON, prom_export CSV, integrity JSON,
#                            run-order.csv); no file over 10 MB (the pre-commit hook enforces it)
#   ../results/raw-samples/  full per-request k6 samples, *.k6.csv.gz, NOT committed (gitignored);
#                            only MANIFEST.json (bytes, sha256, rows, command, testid) is committed
SHELL := bash
.DEFAULT_GOAL := help

ROOT      := ../../..
# Machine-specific port overrides (PROM_PORT, GRAFANA_PORT, TOXIPROXY_API_PORT...): repo-root lab.env,
# gitignored, copied from lab.env.example. Optional: defaults below apply without it. `export` passes
# them on to docker compose (port mappings) and to chaos/toxiproxy.py.
-include $(ROOT)/lab.env
export
# Git Bash on Windows rewrites "/lab/..." arguments of docker.exe into Windows paths; keep them as written.
MSYS_NO_PATHCONV := 1

RAW       := ../results/raw
SAMPLES   := ../results/raw-samples
ANALYSIS  := ../results/analysis
CHARTS    := ../results/charts
# "python3" may be the Microsoft Store alias on Windows: pick the first interpreter that actually runs.
PY        ?= $(shell for p in python3 python; do $$p -c "import sys" >/dev/null 2>&1 && { echo $$p; break; }; done)
K6_IMAGE  := grafana/k6:1.3.0
LAB_NET   := backend-lab
APP_URL   := http://{{SLUG}}-app:8080
PROM_PORT ?= 9090
PROM_URL  ?= http://localhost:$(PROM_PORT)
PROM_RW   := http://prometheus:9090/api/v1/write
# pandas + matplotlib live in the shared analysis image (build once: make -C ../../.. analysis-image),
# so charts never depend on pip on the host. The repo is mounted at /lab.
ANALYSIS_IMAGE ?= backend-lab/analysis:1
DOCKER_PY := docker run --rm -v "$(abspath $(ROOT)):/lab" -w /lab/topics/{{SLUG}}/experiments $(ANALYSIS_IMAGE) python

# Run parameters (override on the command line). Keep them identical for before and every IMPL.
IMPL      ?= before
SCENARIO  ?= S1
RUN       ?= 1
SCRIPT    ?= constant-rate
RATE      ?= 200
WARMUP    ?= 60s
DURATION  ?= 120s
WARMUP_S  ?= 60
IMPLS     ?= before,a
SCENARIOS ?= S1
RUNS      ?= 5
SEED      ?= 42

TS        := $(shell date -u +%Y%m%dT%H%M%SZ)
TESTID    := $(IMPL)-$(SCENARIO)-$(RUN)
ID        := $(TESTID)-$(TS)
# Per-run sample files used by `report` (pilot runs excluded: they only size RUNS).
K6_SAMPLES = $(foreach f,$(sort $(wildcard $(SAMPLES)/*.k6.csv.gz)),$(if $(findstring -pilot-,$(notdir $(f))),,$(f)))

.PHONY: help up down build reset run run-matrix pilot plan-order integrity report samples-verify env \
        chaos-kill chaos-stop chaos-pause chaos-latency chaos-stall chaos-partition chaos-clear

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-16s %s\n", $$1, $$2}'

up: ## Start the stack with IMPL (default before); needs the backend-lab network (make obs-up at repo root)
	@docker network inspect $(LAB_NET) >/dev/null 2>&1 || docker network create $(LAB_NET) >/dev/null
	IMPL=$(IMPL) docker compose up -d --build --wait

down: ## Stop the stack and delete its volumes
	docker compose down -v

build: ## Build the app image only
	docker compose build app

reset: ## Empty the tables so every run starts from the same data (REPLACE with the topic's seed/reset)
	docker compose exec -T postgres psql -U lab -d lab -c "TRUNCATE item"

plan-order: ## Randomized blocked run order -> results/raw/run-order.csv (IMPLS, SCENARIOS, RUNS, SEED)
	$(PY) $(ROOT)/scripts/stats.py plan-order --impls $(IMPLS) --scenarios $(SCENARIOS) --runs $(RUNS) \
	  --seed $(SEED) --out $(RAW)/run-order.csv

run: ## One run: make run IMPL=before SCENARIO=S1 RUN=1 [SCRIPT=constant-rate RATE=200 ...]
	@mkdir -p $(RAW) $(SAMPLES)
	IMPL=$(IMPL) docker compose up -d --wait --force-recreate app
	$(MAKE) --no-print-directory reset
	@start=$$(date -u +%s); \
	docker run --rm --network $(LAB_NET) \
	  -v "$(CURDIR)/k6:/scripts:ro" -v "$(abspath $(RAW)):/out" -v "$(abspath $(SAMPLES)):/samples" \
	  -e BASE_URL=$(APP_URL) -e TESTID=$(TESTID) -e RATE=$(RATE) -e WARMUP=$(WARMUP) -e DURATION=$(DURATION) \
	  -e SUMMARY_OUT=/out/$(ID).summary.json \
	  -e K6_PROMETHEUS_RW_SERVER_URL=$(PROM_RW) \
	  -e K6_PROMETHEUS_RW_TREND_STATS="p(50),p(95),p(99),avg,max" \
	  $(K6_IMAGE) run -q -o experimental-prometheus-rw --out csv=/samples/$(ID).k6.csv.gz \
	  --tag testid=$(TESTID) /scripts/$(SCRIPT).js; \
	status=$$?; end=$$(date -u +%s); \
	echo "{\"testid\":\"$(TESTID)\",\"id\":\"$(ID)\",\"script\":\"$(SCRIPT)\",\"rate\":$(RATE),\"start\":$$start,\"end\":$$end,\"k6_exit\":$$status}" \
	  > $(RAW)/$(ID).run.json; \
	$(PY) $(ROOT)/scripts/raw_manifest.py update $(SAMPLES) --testid $(TESTID) \
	  --cmd "make run IMPL=$(IMPL) SCENARIO=$(SCENARIO) RUN=$(RUN) SCRIPT=$(SCRIPT) RATE=$(RATE) WARMUP=$(WARMUP) DURATION=$(DURATION)" \
	  || echo "WARN: raw-samples manifest not updated"; \
	$(PY) $(ROOT)/scripts/prom_export.py --prom $(PROM_URL) --start $$start --end $$end --step 5s \
	  --preset resources --preset jvm --preset http --label compose_project={{SLUG}} \
	  --out $(RAW)/$(ID)-prom.csv --meta || echo "WARN: Prometheus export failed (is make obs-up running?)"; \
	$(PY) $(ROOT)/scripts/prom_export.py --prom $(PROM_URL) --start $$start --end $$end --step 5s \
	  --preset k6 --label testid=$(TESTID) --out $(RAW)/$(ID)-k6prom.csv --meta || true; \
	exit $$status

run-matrix: ## Run every row of results/raw/run-order.csv in order (seq,block,scenario,impl,run)
	@test -f $(RAW)/run-order.csv || { echo "missing $(RAW)/run-order.csv: make plan-order"; exit 1; }
	@tail -n +2 $(RAW)/run-order.csv | while IFS=, read -r seq block scenario impl run; do \
	  echo "== [$$seq] $$impl $$scenario run $$run"; \
	  $(MAKE) --no-print-directory run IMPL=$$impl SCENARIO=$$scenario RUN=$$run || echo "run $$seq failed (logged in .run.json)"; \
	done

pilot: ## Pilot: 3 runs per impl at S1 to estimate variance before fixing RUNS (04 §2.5)
	$(PY) $(ROOT)/scripts/stats.py plan-order --impls $(IMPLS) --scenarios S1 --runs 3 --seed $(SEED) \
	  --out $(RAW)/pilot-order.csv --force
	@tail -n +2 $(RAW)/pilot-order.csv | while IFS=, read -r seq block scenario impl run; do \
	  $(MAKE) --no-print-directory run IMPL=$$impl SCENARIO=pilot RUN=$$run; \
	done

integrity: ## Check invariants for one run: make integrity TESTID_RUN=before-F1-1 K6_CSV=../results/raw-samples/<id>.k6.csv.gz
	$(PY) checker/integrity_check.py --testid $(TESTID_RUN) --k6-csv $(K6_CSV) \
	  --out $(RAW)/$(notdir $(K6_CSV:.k6.csv.gz=))-integrity.json

samples-verify: ## Check local raw-samples/*.csv.gz against the committed MANIFEST.json (STRICT=1: all must be present)
	$(PY) $(ROOT)/scripts/raw_manifest.py verify $(SAMPLES) $(if $(STRICT),--strict)

report: ## Summarize raw-samples/*.k6.csv.gz per run, compare vs before (-> results/analysis), charts via the analysis image
	@mkdir -p $(ANALYSIS) $(CHARTS)
	@test -n "$(K6_SAMPLES)" || { echo "no $(SAMPLES)/*.k6.csv.gz (outside pilot): run the matrix first"; exit 1; }
	$(PY) $(ROOT)/scripts/raw_manifest.py verify $(SAMPLES)
	$(PY) $(ROOT)/scripts/stats.py summarize --input $(K6_SAMPLES) --format k6 --metric http_req_duration \
	  --skip-seconds $(WARMUP_S) --out $(ANALYSIS)/runs.csv
	for m in p50 p95 p99; do \
	  $(PY) $(ROOT)/scripts/stats.py compare --summary $(ANALYSIS)/runs.csv --baseline before --metric $$m \
	    --out $(ANALYSIS)/compare-$$m.csv; done
	$(PY) $(ROOT)/scripts/stats.py compare --summary $(ANALYSIS)/runs.csv --baseline before --metric throughput_per_s \
	  --higher-is-better --out $(ANALYSIS)/compare-throughput.csv
	@docker image inspect $(ANALYSIS_IMAGE) >/dev/null 2>&1 || { echo "missing $(ANALYSIS_IMAGE): make -C $(ROOT) analysis-image"; exit 1; }
	$(DOCKER_PY) charts/plot.py ci-bar --groups $(ANALYSIS)/runs.groups.csv --metric p99 --out $(CHARTS)/p99-ci.png
	for s in $$(echo "$(SCENARIOS)" | tr ',' ' '); do \
	  $(DOCKER_PY) charts/plot.py cdf --k6 $(K6_SAMPLES) --scenario $$s --out $(CHARTS)/$$s-latency-cdf.png; done

env: ## Write results/env.md from real commands (run before the matrix)
	@{ echo "# Môi trường chạy thí nghiệm — {{TOPIC}}"; echo; echo "Sinh tự động bởi \`make env\` lúc $$(date -u +%Y-%m-%dT%H:%M:%SZ)."; echo; \
	  echo '```'; uname -a 2>/dev/null || ver; echo; docker version --format 'Docker {{.Server.Version}} (API {{.Server.APIVersion}})'; \
	  docker compose version; docker info --format 'Docker VM: {{.NCPU}} CPU, {{.MemTotal}} bytes RAM, kernel {{.KernelVersion}}'; \
	  docker run --rm $(K6_IMAGE) version; echo; cat .env; echo '```'; } > ../results/env.md
	@echo "wrote ../results/env.md — add CPU model, laptop power state and anything unusual by hand"

chaos-kill: ## SIGKILL a service: make chaos-kill SVC=app
	bash chaos/container.sh kill $(SVC) | tee -a $(RAW)/chaos.jsonl

chaos-stop: ## SIGTERM then SIGKILL (rolling-restart-like): make chaos-stop SVC=app
	bash chaos/container.sh stop $(SVC) | tee -a $(RAW)/chaos.jsonl

chaos-pause: ## Freeze a service N seconds: make chaos-pause SVC=postgres SECONDS=10
	bash chaos/container.sh pause $(SVC) $(SECONDS) | tee -a $(RAW)/chaos.jsonl

chaos-latency: ## Add latency on app->postgres: make chaos-latency MS=200 JITTER=50
	$(PY) chaos/toxiproxy.py latency --ms $(MS) --jitter $(or $(JITTER),0) | tee -a $(RAW)/chaos.jsonl

chaos-stall: ## Stop data flow without closing connections (gray failure)
	$(PY) chaos/toxiproxy.py timeout --ms 0 | tee -a $(RAW)/chaos.jsonl

chaos-partition: ## Cut app->postgres (proxy disabled)
	$(PY) chaos/toxiproxy.py partition | tee -a $(RAW)/chaos.jsonl

chaos-clear: ## Remove all toxics and re-enable the proxy
	$(PY) chaos/toxiproxy.py clear | tee -a $(RAW)/chaos.jsonl
