.PHONY: help install install-dev test test-unit test-integration test-property test-cov clean format lint run docker-build docker-up docker-down

help:
	@echo "Real-Time Voice Assistant - Development Commands"
	@echo "================================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install core dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-property    Run property-based tests only"
	@echo "  make test-cov         Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format           Format code with black and isort"
	@echo "  make lint             Run linters (flake8, mypy)"
	@echo ""
	@echo "Running:"
	@echo "  make run              Run the application"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-up        Start with docker-compose"
	@echo "  make docker-down      Stop docker-compose"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove generated files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest

test-unit:
	pytest -m unit

test-integration:
	pytest -m integration

test-property:
	pytest -m property

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .hypothesis
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

format:
	black src/ tests/
	isort src/ tests/

lint:
	flake8 src/ tests/
	mypy src/

run:
	python -m src.main

docker-build:
	docker build -t realtime-voice-assistant .

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down
