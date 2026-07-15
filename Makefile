.PHONY: help install dev up down migrate test test-all lint format typecheck check web

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install the package with dev dependencies
	pip install -e ".[dev]"

up: ## Start Postgres + Redis (Docker)
	docker-compose up -d postgres redis

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

lint: ## Ruff lint
	ruff check .

format: ## Ruff format
	ruff format .

typecheck: ## mypy on apps + packages
	mypy apps packages

check: lint typecheck test ## Lint + typecheck + offline tests
	ruff format --check .
