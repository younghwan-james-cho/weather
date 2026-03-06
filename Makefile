.PHONY: all check format lint test clean

# Run all checks
all: check

# Run all validation checks
check: lint format-check
	@echo "✓ All checks passed"

# Run ruff linting
lint:
	uv run ruff check .

# Run ruff formatting check
format-check:
	uv run ruff format . --check

# Format code
format:
	uv run ruff format .

# Run tests (if tests directory exists)
test:
	@if [ -d "tests" ]; then \
		uv run pytest tests/ -v; \
	else \
		echo "No tests directory"; \
	fi

# Clean generated files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
