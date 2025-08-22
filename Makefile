# FundCast Development Makefile

.PHONY: help dev test lint bench build up down clean install check security

# Default target
help:
	@echo "FundCast Development Commands"
	@echo "============================="
	@echo ""
	@echo "Development:"
	@echo "  dev        Start development servers (API + UI)"
	@echo "  install    Install dependencies"
	@echo "  check      Run all checks (lint + test + security)"
	@echo ""
	@echo "Testing:"
	@echo "  test       Run all tests with coverage"
	@echo "  test-unit  Run unit tests only"
	@echo "  test-e2e   Run end-to-end tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint       Run linting and formatting"
	@echo "  security   Run security scans"
	@echo "  bench      Run performance benchmarks"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  build      Build Docker containers"
	@echo "  up         Start with docker-compose"
	@echo "  down       Stop docker-compose"
	@echo "  clean      Clean build artifacts"
	@echo ""
	@echo "Utilities:"
	@echo "  sbom       Generate Software Bill of Materials"
	@echo "  migrate    Run database migrations"

# Development
dev:
	@echo "Starting FundCast development environment..."
	@docker-compose -f docker-compose.dev.yml up --build

install:
	@echo "Installing Python dependencies..."
	@pip install -e ".[dev,security]"
	@echo "Installing Node.js dependencies..."
	@cd src/ui && npm install

# Testing
test:
	@echo "Running comprehensive test suite..."
	@python -m pytest tests/ \
		--cov=src \
		--cov-report=html:htmlcov \
		--cov-report=xml \
		--cov-report=term-missing \
		--cov-fail-under=95 \
		-v

test-unit:
	@echo "Running unit tests..."
	@python -m pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	@python -m pytest tests/test_integration.py -v

test-e2e:
	@echo "Running end-to-end tests..."
	@python -m pytest tests/e2e/ -v

# Code Quality
lint:
	@echo "Running code quality checks..."
	@echo "→ Python linting with ruff..."
	@ruff check src/ tests/
	@echo "→ Python type checking with mypy..."
	@mypy src/
	@echo "→ Python formatting with black..."
	@black --check src/ tests/
	@echo "→ Python import sorting..."
	@isort --check-only src/ tests/
	@echo "→ Node.js linting..."
	@cd src/ui && npm run lint

format:
	@echo "Formatting code..."
	@black src/ tests/
	@isort src/ tests/
	@cd src/ui && npm run format

security:
	@echo "Running security scans..."
	@echo "→ Python security scan with bandit..."
	@bandit -r src/ -f json -o security-report.json
	@echo "→ Dependency vulnerability check..."
	@safety check --json --output safety-report.json
	@echo "→ SAST scan with semgrep..."
	@semgrep --config=auto src/ --json --output=semgrep-report.json
	@echo "Security reports generated: security-report.json, safety-report.json, semgrep-report.json"

# Performance
bench:
	@echo "Running performance benchmarks..."
	@python -m pytest tests/benchmarks/ -v --benchmark-only
	@echo "→ API endpoint benchmarks..."
	@python scripts/benchmark_api.py
	@echo "→ Database query benchmarks..."
	@python scripts/benchmark_db.py

# Build & Deploy
build:
	@echo "Building Docker containers..."
	@docker build -t fundcast-api -f deploy/Dockerfile .
	@docker build -t fundcast-ui -f src/ui/Dockerfile src/ui/

up:
	@echo "Starting FundCast with docker-compose..."
	@docker-compose up --build -d
	@echo "Services available at:"
	@echo "  API: http://localhost:8000"
	@echo "  UI:  http://localhost:3000"
	@echo "  Docs: http://localhost:8000/docs"

down:
	@echo "Stopping FundCast services..."
	@docker-compose down

logs:
	@docker-compose logs -f

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf __pycache__ .pytest_cache .coverage htmlcov/
	@rm -rf src/ui/node_modules src/ui/.next src/ui/out
	@rm -rf dist/ build/ *.egg-info/
	@docker system prune -f

# Database
migrate:
	@echo "Running database migrations..."
	@alembic upgrade head

migrate-create:
	@echo "Creating new migration..."
	@read -p "Migration name: " name; \
	alembic revision --autogenerate -m "$$name"

# Utilities
sbom:
	@echo "Generating Software Bill of Materials..."
	@pip-audit --format=json --output=sbom-python.json
	@cd src/ui && npm audit --json > ../sbom-node.json
	@echo "SBOM files generated: sbom-python.json, sbom-node.json"

check: lint security test
	@echo "✅ All checks passed!"

# Environment setup
env:
	@echo "Setting up development environment..."
	@cp .env.example .env
	@echo "⚠️  Please update .env with your configuration"

# CI/CD helpers
ci-install:
	@pip install -e ".[dev,security]"

ci-test:
	@python -m pytest tests/ --cov=src --cov-report=xml --cov-fail-under=95

ci-security:
	@bandit -r src/ -f json -o security-report.json || true
	@safety check --json --output safety-report.json || true
	@semgrep --config=auto src/ --json --output=semgrep-report.json || true

# Development helpers
shell:
	@python -c "import IPython; IPython.start_ipython(['--profile-dir=.'])"

docs:
	@echo "Starting documentation server..."
	@mkdocs serve

docs-build:
	@echo "Building documentation..."
	@mkdocs build

# Monitoring
monitor:
	@echo "Starting monitoring stack..."
	@docker-compose -f docker-compose.monitoring.yml up -d

monitor-down:
	@docker-compose -f docker-compose.monitoring.yml down