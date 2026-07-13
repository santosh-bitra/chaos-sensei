.PHONY: help install install-dev test lint format check clean

help:
	@echo "Chaos Sensei Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install package"
	@echo "  make install-dev   Install package with dev dependencies"
	@echo ""
	@echo "Quality:"
	@echo "  make test          Run tests"
	@echo "  make lint          Run linters (ruff, mypy)"
	@echo "  make format        Format code (black, isort)"
	@echo "  make check         Run all checks (test, lint, format)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean         Remove build artifacts"
	@echo "  make build         Build distribution"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest -v --cov=chaos_sensei --cov-report=term-missing

test-fast:
	pytest -v

lint:
	ruff check chaos_sensei tests
	mypy chaos_sensei

format:
	black chaos_sensei tests
	isort chaos_sensei tests

check: lint test
	@echo "All checks passed!"

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov

build: clean
	python -m build

run-help:
	python -m chaos_sensei.cli --help

example-scan:
	python -m chaos_sensei.cli scan --help
