# issue-analyzer

A Python tool to download all GitHub issues from a repository (including comments) and save them to a JSON file for later LLM analysis.

## Quick Start

```bash
# Download all issues from a repository to SQLite database
./issue_downloader.py rancher/dartboard

# Export issues from SQLite database to JSON
./issue_summarizer.py dartboard_issues.db

# Or specify custom output files
./issue_downloader.py rancher/dartboard issues.db
./issue_summarizer.py issues.db issues.json

# Use with GitHub token for higher rate limits
export GITHUB_TOKEN=your_token
./issue_downloader.py rancher/dartboard
```

## Features

- **Two-stage workflow**: Download issues to SQLite first, then export to JSON
- **Resilient data fetching**: Data is stored in a SQLite database as it is fetched, providing resilience against network errors and power loss
- **Resume capability**: On restart, the downloader resumes from where it left off, skipping issues already in the database
- **Automatic retry**: Retries failed HTTP requests up to 10 times with exponential backoff
- **Detailed error logging**: Logs full response body on HTTP errors for debugging

### Resume Behavior

The `issue_downloader.py` script creates a SQLite database file. If the script is interrupted or fails:

1. Re-run the same command to resume from where it left off
2. Issues already in the database will be skipped
3. Only new issues will be fetched

**Note**: Issues already in the database are not refreshed on subsequent runs. To get fresh data, delete the database file.

## Requirements

- [uv](https://docs.astral.sh/uv/) - Fast Python package installer

## Installation

No installation required! The script uses inline dependencies via uv. Install uv following the [official instructions](https://docs.astral.sh/uv/getting-started/installation/).

## Development

See [HACKING.md](HACKING.md) for development instructions.

## AI Agent Integration

See [AGENTS.md](AGENTS.md) for instructions on using this tool with AI coding agents.

## License

MIT License - see [LICENSE](LICENSE) for details.
