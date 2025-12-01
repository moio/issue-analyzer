# issue-analyzer

A Python tool to download all GitHub issues from a repository (including comments) and save them to a JSON file for later LLM analysis.

## Quick Start

```bash
# Download all issues from a repository
./issue_analyzer.py rancher/dartboard

# Save to a specific file
./issue_analyzer.py rancher/dartboard issues.json

# Use with GitHub token for higher rate limits
export GITHUB_TOKEN=your_token
./issue_analyzer.py rancher/dartboard
```

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
