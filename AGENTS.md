# AI Agent Instructions

This document provides instructions for AI coding agents working on this repository.

## Project Overview

Issue Analyzer is a Python tool that downloads all GitHub issues (including comments) from a repository and saves them to SQLite and JSON files.

## Key Technical Details

- **Dependency Management**: Uses [uv](https://docs.astral.sh/uv/) with PEP 723 inline script dependencies
- **Python Version**: Requires Python 3.10+
- **No pyproject.toml**: Dependencies are embedded directly in each script's header
- **Primary Scripts**: 
  - `issue_downloader.py` - Downloads issues to SQLite database
  - `issue_summarizer.py` - Exports issues from SQLite to JSON

## Running Commands

```bash
# Download issues to SQLite database
./issue_downloader.py <owner>/<repo> [output.db]

# Export issues from SQLite to JSON
./issue_summarizer.py <input.db> [output.json]

# Format code
make format

# Lint code
make lint

# Run end-to-end tests
make e2e

# Run all checks
make all
```

## Adding Dependencies

Add dependencies to the script header in each script:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31.0",
#     "new-package>=1.0.0",  # Add here
# ]
# ///
```

## Testing

- E2E tests run against `rancher/dartboard` and `rancher/rancher` repositories
- Run `make all` before committing
