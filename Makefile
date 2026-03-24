.PHONY: setup test lint format type-check security-check infra-up infra-down seed-data run demo clean help

PYTHON := python3.12
VENV := .venv
BIN := $(VENV)/bin

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────

setup: ## Create virtual environment and install all dependencies
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev,spark]"
	$(BIN)/pre-commit install
	@echo "✅ Setup complete. Activate with: source $(VENV)/bin/activate"

# ─────────────────────────────────────────────
# Quality checks
# ─────────────────────────────────────────────

test: ## Run all tests with coverage
	$(BIN)/pytest

test-unit: ## Run unit tests only
	$(BIN)/pytest tests/unit/ -v

test-integration: ## Run integration tests only
	$(BIN)/pytest tests/integration/ -v

lint: ## Run ruff linter
	$(BIN)/ruff check src/ tests/

format: ## Auto-format code with ruff
	$(BIN)/ruff format src/ tests/
	$(BIN)/ruff check --fix src/ tests/

type-check: ## Run mypy type checking
	$(BIN)/mypy src/

security-check: ## Run bandit security linter
	$(BIN)/bandit -r src/ -c pyproject.toml

check-all: lint type-check security-check test ## Run all quality checks

# ─────────────────────────────────────────────
# Infrastructure
# ─────────────────────────────────────────────

infra-up: ## Start local dev infrastructure (Kafka, PostgreSQL, LocalStack)
	docker compose -f infrastructure/docker/docker-compose.yml up -d
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 10
	@echo "✅ Infrastructure ready."

infra-down: ## Stop local dev infrastructure
	docker compose -f infrastructure/docker/docker-compose.yml down -v
	@echo "✅ Infrastructure stopped."

infra-logs: ## Tail logs from local infrastructure
	docker compose -f infrastructure/docker/docker-compose.yml logs -f

# ─────────────────────────────────────────────
# Data & Pipeline
# ─────────────────────────────────────────────

seed-data: ## Generate synthetic test documents
	$(BIN)/python scripts/seed_data.py
	@echo "✅ Synthetic data generated."

run: ## Run the API server locally
	$(BIN)/uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

demo: ## Run end-to-end demo
	$(BIN)/python scripts/run_demo.py

# ─────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	rm -rf $(VENV) .mypy_cache .pytest_cache .ruff_cache .coverage htmlcov dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned."
