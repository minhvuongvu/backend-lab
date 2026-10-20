SHELL := bash
.DEFAULT_GOAL := help

OBS_COMPOSE := docker compose -f shared/observability/docker-compose.yml
LAB_NETWORK := backend-lab
# OBS=full (metrics + logs + traces + profiles) or OBS=metrics (Prometheus + Grafana + docker-stats only)
OBS ?= full

.PHONY: help obs-up obs-down obs-status lab-network new-topic insights

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

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
	@curl -s http://localhost:$${PROM_PORT:-9090}/api/v1/targets | python3 -c "import sys,json;[print(f\"{t['labels'].get('job'):14} {t['labels'].get('instance'):45} {t['health']}\") for t in json.load(sys.stdin)['data']['activeTargets']]" || true

new-topic: ## Create a topic from templates: make new-topic SLUG=transactional-outbox
	@test -n "$(SLUG)" || { echo "Usage: make new-topic SLUG=<kebab-case-slug>"; exit 1; }
	@bash scripts/new-topic.sh "$(SLUG)"

insights: ## Rebuild INSIGHTS.html from every topic (and check insight structure)
	python3 scripts/build_insights.py
	python3 scripts/build_insights.py --check
