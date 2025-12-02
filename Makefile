.PHONY: all format lint e2e clean

# Default target runs all checks
all: lint e2e

# Format code with Black
format:
	uv run --with black black issue_downloader.py issue_summarizer.py

# Lint code (check formatting)
lint:
	uv run --with black black --check issue_downloader.py issue_summarizer.py

# Run end-to-end tests
e2e:
	@echo "Running e2e test against rancher/dartboard (limit 100)..."
	@if [ -z "$$GITHUB_TOKEN" ]; then \
		echo "Warning: GITHUB_TOKEN not set. May hit rate limits."; \
	fi
	./issue_downloader.py --limit 100 rancher/dartboard /tmp/dartboard_issues.db
	./issue_summarizer.py /tmp/dartboard_issues.db /tmp/dartboard_issues.json
	@echo "Verifying output file..."
	@python3 -c "import json; data = json.load(open('/tmp/dartboard_issues.json')); print(f'Downloaded {len(data)} issues'); assert len(data) <= 100, 'Expected at most 100 issues'"
	@rm -f /tmp/dartboard_issues.json /tmp/dartboard_issues.db
	@echo "E2E test 1 passed!"
	@echo ""
	@echo "Running e2e test against rancher/rancher (limit 100)..."
	./issue_downloader.py --limit 100 rancher/rancher /tmp/rancher_issues.db
	./issue_summarizer.py /tmp/rancher_issues.db /tmp/rancher_issues.json
	@echo "Verifying output file..."
	@python3 -c "import json; data = json.load(open('/tmp/rancher_issues.json')); print(f'Downloaded {len(data)} issues'); assert len(data) <= 100, 'Expected at most 100 issues'"
	@rm -f /tmp/rancher_issues.json /tmp/rancher_issues.db
	@echo "E2E test 2 passed!"

# Clean up generated files
clean:
	rm -f *_issues.json *_issues.db
