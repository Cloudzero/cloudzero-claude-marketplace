# Copyright CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

.PHONY: help install install-dev test lint format clean build docker-build docker-up docker-down

# Default target
help:
	@echo "Available targets:"
	@echo "  install        - Install production dependencies"
	@echo "  install-dev    - Install development dependencies"
	@echo "  test           - Run tests with coverage"
	@echo "  lint           - Run linting checks"
	@echo "  format         - Format code"
	@echo "  clean          - Remove build artifacts and caches"
	@echo "  build          - Build distribution packages"
	@echo "  docker-build   - Build Docker image"
	@echo "  docker-up      - Start Docker containers"
	@echo "  docker-down    - Stop Docker containers"

# Python: Install production dependencies
install:
	uv sync

# Python: Install development dependencies
install-dev:
	uv sync --extra dev

# Python: Run tests with coverage
test:
	uv run pytest --cov --cov-report=term-missing --cov-report=html

# Python: Run linting checks
lint:
	uv run ruff check .

# Python: Format code
format:
	uv run ruff format .

# Python: Run all checks (format, lint, test)
check: format lint test

# Clean build artifacts and caches
clean:
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/
	rm -rf htmlcov/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.py,cover" -delete

# Build Python distribution packages
build:
	uv build

# Docker: Build image
docker-build:
	docker build -t template-cloudzero-open-source:latest .

# Docker: Start containers
docker-up:
	docker-compose up -d

# Docker: Stop containers
docker-down:
	docker-compose down

# Docker: View logs
docker-logs:
	docker-compose logs -f

# JavaScript targets (uncomment if needed)
# npm-install:
# 	cd javascript && npm install
#
# npm-test:
# 	cd javascript && npm test
#
# npm-lint:
# 	cd javascript && npm run lint
#
# npm-format:
# 	cd javascript && npm run format
