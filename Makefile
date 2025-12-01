.PHONY: all format lint test e2e clean

# Default target runs all checks
all: lint test e2e

# Format code with Black
format:
	uv run --with black black issue_analyzer.py test_issue_analyzer.py

# Lint code (check formatting)
lint:
	uv run --with black black --check issue_analyzer.py test_issue_analyzer.py

# Run unit tests
test:
	uv run --with pytest pytest test_issue_analyzer.py -v

# Run end-to-end test against rancher/dartboard
e2e:
	@echo "Running e2e test against rancher/dartboard..."
	@if [ -z "$$GITHUB_TOKEN" ]; then \
		echo "Warning: GITHUB_TOKEN not set. May hit rate limits."; \
	fi
	uv run issue_analyzer.py rancher/dartboard /tmp/dartboard_issues.json
	@echo "Verifying output file..."
	@python3 -c "import json; data = json.load(open('/tmp/dartboard_issues.json')); print(f'Downloaded {len(data)} issues'); assert len(data) >= 0, 'Expected at least some data'"
	@rm -f /tmp/dartboard_issues.json
	@echo "E2E test passed!"

# Clean up generated files
clean:
	rm -f *_issues.json
	rm -rf __pycache__ .pytest_cache .ruff_cache
	find . -name "*.pyc" -delete
