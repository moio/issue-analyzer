# AI Agent Instructions

This document provides instructions for AI coding agents working on this repository.

## Project Overview

Issue Analyzer is a Python tool that downloads all GitHub issues (including comments) from a repository and saves them to a JSON file.

## Key Technical Details

- **Dependency Management**: Uses [uv](https://docs.astral.sh/uv/) with PEP 723 inline script dependencies
- **Python Version**: Requires Python 3.10+
- **No pyproject.toml**: Dependencies are embedded directly in the script header
- **Primary Script**: `issue_analyzer.py`

## Running Commands

```bash
# Run the main script
./issue_analyzer.py <owner>/<repo> [output.json]

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

Add dependencies to the script header in `issue_analyzer.py`:

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

- E2E tests run against `rancher/dartboard` repository
- Run `make all` before committing
