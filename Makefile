# On Windows, a bare "bash" can resolve to the WSL launcher (C:\Windows\System32\bash.exe); use Git Bash.
ifeq ($(OS),Windows_NT)
  GIT_BASH := $(wildcard C:/PROGRA~1/Git/bin/bash.exe)
  SHELL := $(if $(GIT_BASH),$(GIT_BASH),bash)
else
  SHELL := bash
endif
.DEFAULT_GOAL := help

# Machine-specific port overrides (PROM_PORT, GRAFANA_PORT, OTLP_*_PORT, ...): see lab.env.example.
-include lab.env
export

ROOT := $(CURDIR)
ANALYSIS_IMAGE := backend-lab/analysis:1

# "python3" may be the Microsoft Store alias on Windows: pick the first interpreter that actually runs.
PYTHON ?= $(shell for p in python3 python; do $$p -c "import sys" >/dev/null 2>&1 && { echo $$p; break; }; done)

OBS_COMPOSE := docker compose -f shared/observability/docker-compose.yml
LAB_NETWORK := backend-lab
# OBS=full (metrics + logs + traces + profiles) or OBS=metrics (Prometheus + Grafana + docker-stats only)
OBS ?= full

.PHONY: help doctor analysis-image analysis lab-network obs-up obs-down obs-status new-topic roadmap pages insights questions hubs hubs-check test check hooks

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

doctor: ## Check this machine can run the lab (tools, JDK 21, Docker, ports, TLS, git remote)
	@"$(SHELL)" scripts/doctor.sh

analysis-image: ## Build the pinned pandas/matplotlib image used for experiment analysis and charts
	docker build -t $(ANALYSIS_IMAGE) shared/analysis

analysis: ## Run a command in the analysis image with the repo at /lab: make analysis CMD="python scripts/stats.py ..."
	$(if $(CMD),,$(error Usage: make analysis CMD="python <script> ..."))
	@docker image inspect $(ANALYSIS_IMAGE) >/dev/null 2>&1 || $(MAKE) analysis-image
	MSYS_NO_PATHCONV=1 docker run --rm -v "$(ROOT):/lab" -w /lab $(ANALYSIS_IMAGE) $(CMD)

# ---- observability ----
lab-network: ## Create the shared docker network topics and the obs stack join
	@docker network inspect $(LAB_NETWORK) >/dev/null 2>&1 || docker network create $(LAB_NETWORK) >/dev/null
	@echo "network $(LAB_NETWORK) ready"

obs-up: lab-network ## Start observability: make obs-up [OBS=full|metrics] [PROM_PORT=..] [GRAFANA_PORT=..]
	COMPOSE_PROFILES=$(if $(filter full,$(OBS)),full,) $(OBS_COMPOSE) up -d --remove-orphans
	@echo "Prometheus: http://localhost:$${PROM_PORT:-9090}  |  Grafana: http://localhost:$${GRAFANA_PORT:-3000} (admin/admin)"
	@echo "OTLP: localhost:$${OTLP_GRPC_PORT:-4317} (gRPC) / $${OTLP_HTTP_PORT:-4318} (HTTP)  |  Pyroscope: localhost:$${PYROSCOPE_PORT:-4040}"

obs-down: ## Stop the whole observability stack (all profiles)
	$(OBS_COMPOSE) --profile '*' down

obs-status: ## Show observability containers and Prometheus target health
	$(OBS_COMPOSE) --profile '*' ps
	@curl -s http://localhost:$${PROM_PORT:-9090}/api/v1/targets | $(PYTHON) -c "import sys,json;[print(f\"{t['labels'].get('job'):14} {t['labels'].get('instance'):45} {t['health']}\") for t in json.load(sys.stdin)['data']['activeTargets']]" || true

# ---- topics & pages ----
new-topic: ## Create a topic from templates: make new-topic SLUG=transactional-outbox
	@test -n "$(SLUG)" || { echo "Usage: make new-topic SLUG=<kebab-case-slug>"; exit 1; }
	@"$(SHELL)" scripts/new-topic.sh "$(SLUG)"

roadmap: ## Re-number and regroup hub/roadmap.html (learning order), validate prerequisites and learning paths
	$(PYTHON) scripts/roadmap_order.py

pages: ## Regenerate index.html (from README.md) and hub/rules.html (from CLAUDE.md)
	$(PYTHON) scripts/build_pages.py

insights: ## Rebuild hub/insights.html from every topic (and check insight structure)
	$(PYTHON) scripts/build_insights.py
	$(PYTHON) scripts/build_insights.py --check

questions: ## Rebuild hub/questions.html from every topic's Q&A log (and check Q&A / suggested-question markup)
	$(PYTHON) scripts/build_questions.py
	$(PYTHON) scripts/build_questions.py --check

hubs: pages ## Rebuild every hub page (lab, insights, problems, glossary, benchmarks, questions, home, rules) + related topics
	$(PYTHON) scripts/build_insights.py
	$(PYTHON) scripts/build_knowledge.py
	$(PYTHON) scripts/build_questions.py
	$(PYTHON) scripts/build_dashboard.py

hubs-check: ## Lint insight, problem/glossary, Q&A and benchmark markup of every topic
	$(PYTHON) scripts/build_insights.py --check
	$(PYTHON) scripts/build_knowledge.py --check
	$(PYTHON) scripts/build_questions.py --check
	$(PYTHON) scripts/build_dashboard.py --check

# ---- quality: unit tests, linters, render check, git hook ----
test: ## Unit tests for the lab scripts (stdlib unittest, no dependencies)
	PYTHONIOENCODING=utf-8 $(PYTHON) -m unittest discover -s tests -v

check: test ## All checks: unit tests, roadmap + hub linters, generated pages up to date, syntax, headless render check
	@out="$$($(PYTHON) scripts/roadmap_order.py --check)"; echo "$$out"; echo "$$out" | grep -q 'learning-path order problems: 0'
	$(PYTHON) scripts/build_insights.py --check --no-page
	$(PYTHON) scripts/build_knowledge.py --check --no-page
	$(PYTHON) scripts/build_questions.py --check --no-page
	$(PYTHON) scripts/build_dashboard.py --check
	$(PYTHON) scripts/build_pages.py --check
	$(PYTHON) -m py_compile scripts/*.py
	@for f in scripts/*.sh scripts/hooks/pre-commit; do "$(SHELL)" -n "$$f" || exit 1; done; echo "shell syntax ok"
	$(PYTHON) scripts/check_render.py

hooks: ## Install the git pre-commit hook (fast checks; LAB_RENDER_CHECK=1 adds the render check)
	cp scripts/hooks/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "pre-commit hook installed"
