.PHONY: help install dev test clean run docker-build docker-run format lint

# Default target
help:
	@echo "Available commands:"
	@echo "  install     Install dependencies"
	@echo "  dev         Install development dependencies"
	@echo "  test        Run tests"
	@echo "  run         Run the development server"
	@echo "  clean       Clean up temporary files"
	@echo "  format      Format code with black"
	@echo "  lint        Run linting with flake8"
	@echo "  docker-build Build Docker image"
	@echo "  docker-run  Run Docker container"

# Install dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
dev: install
	pip install pytest pytest-cov black flake8 httpx

# Run tests
test:
	pytest

# Run tests with coverage
test-cov:
	pytest --cov=main --cov-report=html --cov-report=term

# Run development server
run:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Clean up temporary files
clean:
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

# Format code
format:
	black main.py test_main.py

# Lint code
lint:
	flake8 main.py test_main.py --max-line-length=100

# Build Docker image
docker-build:
	docker build -t notes-api .

# Run Docker container
docker-run:
	docker run -p 8000:8000 --env-file .env notes-api

# Run with docker-compose
docker-dev:
	docker-compose up --build

# Stop docker-compose
docker-stop:
	docker-compose down

# Setup environment
setup: dev
	@echo "Copying environment template..."
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "Setup complete! Don't forget to:"
	@echo "1. Add your Firebase service account key"
	@echo "2. Update .env with your Firebase project details"

# Quick start for new developers
quickstart: setup
	@echo "Running tests to verify setup..."
	pytest
	@echo "Starting development server..."
	make run