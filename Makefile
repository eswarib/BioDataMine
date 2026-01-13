# BioDataMine Makefile
# ====================
# Convenient shortcuts for common Docker Compose operations

.PHONY: help build up down restart logs logs-api logs-frontend logs-mongo status clean shell-api shell-mongo test

# Default target
help:
	@echo ""
	@echo "BioDataMine Development Commands"
	@echo "================================="
	@echo ""
	@echo "  make build         Build all Docker images"
	@echo "  make up            Start all services (detached)"
	@echo "  make down          Stop all services"
	@echo "  make restart       Restart all services"
	@echo ""
	@echo "  make logs          Follow logs from all services"
	@echo "  make logs-api      Follow backend API logs"
	@echo "  make logs-frontend Follow frontend logs"
	@echo "  make logs-mongo    Follow MongoDB logs"
	@echo ""
	@echo "  make status        Show container status"
	@echo "  make clean         Stop services and remove volumes (clears DB!)"
	@echo ""
	@echo "  make shell-api     Open shell in API container"
	@echo "  make shell-mongo   Open mongo shell"
	@echo ""
	@echo "Quick Start:"
	@echo "  make build up      # Build and start everything"
	@echo ""
	@echo "URLs (when running):"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  API:       http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo ""

# Build all images
build:
	docker compose build

# Start all services in detached mode
up:
	docker compose up -d
	@echo ""
	@echo "✓ BioDataMine is starting..."
	@echo "  Frontend:  http://localhost:3000"
	@echo "  API:       http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo ""
	@echo "Run 'make logs' to follow the logs"

# Start with build (rebuild images before starting)
up-build:
	docker compose up -d --build

# Start in foreground (useful for debugging)
up-fg:
	docker compose up

# Stop all services
down:
	docker compose down

# Restart all services
restart: down up

# Follow all logs
logs:
	docker compose logs -f

# Follow specific service logs
logs-api:
	docker compose logs -f datascan-api

logs-frontend:
	docker compose logs -f frontend

logs-mongo:
	docker compose logs -f mongo

# Show container status
status:
	@echo ""
	@echo "Container Status:"
	@echo "-----------------"
	@docker compose ps
	@echo ""

# Stop and remove everything including volumes (destructive!)
clean:
	@echo "⚠️  This will remove all data including the database!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker compose down -v --remove-orphans
	@echo "✓ All containers and volumes removed"

# Open shell in API container
shell-api:
	docker compose exec datascan-api /bin/bash

# Open mongo shell
shell-mongo:
	docker compose exec mongo mongosh datascan

# Run backend tests (if available)
test:
	docker compose exec datascan-api python -m pytest

# Pull latest base images
pull:
	docker compose pull






