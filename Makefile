.PHONY: help lint format format-check test build build-podman clean doctor validate-compose install install-dev

# Default target
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RESET := \033[0m

help: ## Show this help message
	@echo "$(CYAN)Minecraft Launcher - Available Targets:$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

install: ## Install runtime dependencies
	@echo "$(CYAN)Installing runtime dependencies...$(RESET)"
	pip3 install -r requirements.txt

install-dev: ## Install development dependencies (includes ruff)
	@echo "$(CYAN)Installing development dependencies...$(RESET)"
	pip3 install -r requirements-dev.txt

lint: ## Run ruff linter on Python code
	@echo "$(CYAN)Running ruff linter...$(RESET)"
	ruff check .

lint-fix: ## Run ruff linter and auto-fix issues
	@echo "$(CYAN)Running ruff linter with auto-fix...$(RESET)"
	ruff check --fix .

format: ## Format Python code with ruff
	@echo "$(CYAN)Formatting Python code with ruff...$(RESET)"
	ruff format .

format-check: ## Check Python code formatting without modifying files
	@echo "$(CYAN)Checking Python code formatting...$(RESET)"
	ruff format --check .

test: ## Run Python syntax checks and basic validation
	@echo "$(CYAN)Running Python syntax checks...$(RESET)"
	python3 -m py_compile minecraft.py
	python3 -m py_compile gui.py
	python3 -m py_compile cli.py
	python3 -m py_compile core/*.py
	@echo "$(GREEN)✓ Python syntax validation passed$(RESET)"

validate-compose: ## Validate Docker Compose files
	@echo "$(CYAN)Validating Docker Compose files...$(RESET)"
	@export DISPLAY=:0 XAUTHORITY=/tmp/.Xauthority USER=testuser && \
	docker compose -f compose.base.yaml config > /dev/null && \
	echo "$(GREEN)✓ Compose files validated$(RESET)"

build: ## Build container image with Docker
	@echo "$(CYAN)Building container image with Docker...$(RESET)"
	docker build -f Containerfile -t tlauncher-java .
	@echo "$(GREEN)✓ Docker build completed$(RESET)"

build-podman: ## Build container image with Podman
	@echo "$(CYAN)Building container image with Podman...$(RESET)"
	podman build -f Containerfile -t tlauncher-java .
	@echo "$(GREEN)✓ Podman build completed$(RESET)"

doctor: ## Run system diagnostics
	@echo "$(CYAN)Running system diagnostics...$(RESET)"
	./minecraft.py doctor

clean: ## Clean up Python cache and temporary files
	@echo "$(CYAN)Cleaning up...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup completed$(RESET)"

ci: format-check lint test ## Run all CI checks (format, lint, test)
	@echo "$(GREEN)✓ All CI checks passed$(RESET)"

all: clean install-dev ci build ## Run full development workflow
	@echo "$(GREEN)✓ Full workflow completed$(RESET)"
