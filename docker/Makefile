# Docker Makefile for Real-Time Voice Assistant

.PHONY: help build build-dev up up-dev down down-dev logs logs-dev restart restart-dev clean test shell

# Default target
help:
	@echo "Docker Management Commands:"
	@echo ""
	@echo "Production:"
	@echo "  make build        - Build production Docker image"
	@echo "  make up           - Start production containers"
	@echo "  make down         - Stop production containers"
	@echo "  make logs         - View production logs"
	@echo "  make restart      - Restart production containers"
	@echo ""
	@echo "Development:"
	@echo "  make build-dev    - Build development Docker image"
	@echo "  make up-dev       - Start development containers"
	@echo "  make down-dev     - Stop development containers"
	@echo "  make logs-dev     - View development logs"
	@echo "  make restart-dev  - Restart development containers"
	@echo "  make shell        - Open shell in development container"
	@echo "  make test         - Run tests in development container"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean        - Remove all containers, volumes, and images"
	@echo "  make health       - Check container health status"
	@echo ""

# Production targets
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

# Development targets
build-dev:
	docker-compose -f docker-compose.dev.yml build

up-dev:
	docker-compose -f docker-compose.dev.yml up -d

down-dev:
	docker-compose -f docker-compose.dev.yml down

logs-dev:
	docker-compose -f docker-compose.dev.yml logs -f

restart-dev:
	docker-compose -f docker-compose.dev.yml restart

shell:
	docker-compose -f docker-compose.dev.yml exec voice-assistant-dev bash

test:
	docker-compose -f docker-compose.dev.yml exec voice-assistant-dev pytest

# Maintenance targets
clean:
	docker-compose down -v
	docker-compose -f docker-compose.dev.yml down -v
	docker system prune -f

health:
	@echo "Production container health:"
	@docker-compose ps
	@echo ""
	@echo "Development container health:"
	@docker-compose -f docker-compose.dev.yml ps
