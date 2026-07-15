.PHONY: help install dev up down migrate stack test test-all test-cov test-e2e lint format typecheck check web

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install the package with dev dependencies
	pip install -e ".[dev]"

up: ## Start Postgres + Redis (Docker)
	docker-compose up -d postgres redis

stack: ## Start postgres, redis, migrate, api, and worker (full backend for e2e)
	docker-compose up -d postgres redis
	sleep 3
	$(MAKE) migrate
	docker-compose up -d api worker

down: ## Stop the Docker stack
	docker-compose down

migrate: ## Apply database migrations
	alembic upgrade head

dev: ## Run API (reload) locally — sandbox LLM by default
	uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

web: ## Run the Next.js web UI (apps/web) in dev mode
	cd apps/web && npm ci && npm run dev

test: ## Offline unit lane — no services/keys/network (sandbox LLM)
	CLOUDOPT_LLM_MODE=sandbox pytest -m "not integration"

test-all: ## Full suite including integration (requires Postgres via `make up && make migrate`)
	pytest

test-cov: ## Full suite with coverage report (requires Postgres for integration tests)
	pytest --cov=apps --cov=packages --cov-report=term-missing

test-e2e: ## Full stack smoke (Compose + Hurl; optional RUN_PY_E2E=1)
	./scripts/e2e-stack-smoke.sh

lint: ## Ruff lint
	ruff check .

format: ## Ruff format
	ruff format .

typecheck: ## mypy on apps + packages
	mypy apps packages

check: lint typecheck test ## Lint + typecheck + offline tests
	ruff format --check .
