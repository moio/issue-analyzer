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
uv run issue_analyzer.py <owner>/<repo> [output.json]

# Format code
make format

# Lint code
make lint

# Run unit tests
make test

# Run end-to-end tests
make e2e

# Run all checks
make all
```

## File Structure

| File | Purpose |
|------|---------|
| `issue_analyzer.py` | Main script with inline dependencies |
| `test_issue_analyzer.py` | Unit tests (pytest) |
| `Makefile` | Development automation |
| `.github/workflows/ci.yml` | GitHub Actions CI workflow |

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

## Testing Requirements

- All functions should have unit tests
- Tests should not make real API calls (use mocking)
- E2E tests run against `rancher/dartboard` repository
- Run `make all` before committing

## Common Tasks

### Adding a New Feature
1. Implement the feature in `issue_analyzer.py`
2. Add unit tests in `test_issue_analyzer.py`
3. Run `make format` to format code
4. Run `make all` to verify all tests pass

### Fixing a Bug
1. Write a failing test that reproduces the bug
2. Fix the bug in `issue_analyzer.py`
3. Verify the test passes
4. Run `make all` to ensure no regressions
