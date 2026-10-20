SHELL := bash
.DEFAULT_GOAL := help

OBS_COMPOSE := docker compose -f shared/observability/docker-compose.yml

.PHONY: help obs-up obs-down new-topic

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

obs-up: ## Start shared Prometheus + Grafana
	$(OBS_COMPOSE) up -d
	@echo "Prometheus: http://localhost:9090  |  Grafana: http://localhost:3000 (admin/admin)"

obs-down: ## Stop shared Prometheus + Grafana
	$(OBS_COMPOSE) down

new-topic: ## Create a topic from templates: make new-topic SLUG=transactional-outbox
	@test -n "$(SLUG)" || { echo "Usage: make new-topic SLUG=<kebab-case-slug>"; exit 1; }
	@bash scripts/new-topic.sh "$(SLUG)"
