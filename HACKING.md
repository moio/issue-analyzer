# Hacking on Issue Analyzer

This document explains how to develop, test, and contribute to the Issue Analyzer tool.

## Prerequisites

You need [uv](https://docs.astral.sh/uv/) installed. uv is a fast Python package installer and resolver that handles dependencies automatically.

Install uv following the [official instructions](https://docs.astral.sh/uv/getting-started/installation/).

## Running the Tool

The script uses inline script dependencies (PEP 723), so you don't need to install anything manually. Just run:

```bash
./issue_analyzer.py <owner>/<repo> [output.json]
```

For example:
```bash
./issue_analyzer.py rancher/dartboard
```

uv will automatically install the required dependencies on first run.

## Development Commands

All development commands are available through the Makefile:

```bash
# Format code with Black
make format

# Run linting (Black check)
make lint

# Run end-to-end tests against rancher/dartboard
make e2e

# Run all checks (lint + e2e)
make all
```

## GitHub Token

For repositories with many issues, you may hit GitHub's rate limit. Create a personal access token at https://github.com/settings/tokens and set it securely:

```bash
read -s GITHUB_TOKEN
export GITHUB_TOKEN
./issue_analyzer.py rancher/dartboard
```

## How Dependencies Work

This project uses [PEP 723](https://peps.python.org/pep-0723/) inline script metadata. Dependencies are declared directly in the script header:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31.0",
# ]
# ///
```

When you run `./issue_analyzer.py`, uv:
1. Reads the dependency metadata from the script
2. Creates an isolated virtual environment
3. Installs the required packages
4. Executes the script

This means no separate `requirements.txt` or `pyproject.toml` is needed for the main script.

## Adding New Dependencies

To add a new dependency:
1. Add it to the `dependencies` list in the script header
2. Run the script - uv will automatically install the new dependency

## Testing

End-to-end tests verify the complete workflow against a real GitHub repository (rancher/dartboard).
