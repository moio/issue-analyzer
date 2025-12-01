#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31.0",
# ]
# ///
"""
Issue Analyzer - Download all GitHub issues from a repository.

This script downloads all issues (including comments) from a GitHub repository
and saves them to a JSON file for later analysis.

Usage:
    ./issue_analyzer.py <owner>/<repo> [output.json]

Examples:
    ./issue_analyzer.py rancher/dartboard
    ./issue_analyzer.py rancher/dartboard issues.json
    ./issue_analyzer.py --limit 100 rancher/rancher

Environment variables:
    GITHUB_TOKEN: Set for higher rate limits (create at https://github.com/settings/tokens)
"""

import argparse
import json
import os
import re
import sys
from typing import Any

import requests


def get_github_headers() -> dict[str, str]:
    """Get headers for GitHub API requests, including auth if available."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "issue-analyzer",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def parse_link_header(link_header: str | None) -> dict[str, str]:
    """Parse GitHub's Link header to extract pagination URLs."""
    if not link_header:
        return {}

    links = {}
    for part in link_header.split(","):
        match = re.match(r'<([^>]+)>;\s*rel="([^"]+)"', part.strip())
        if match:
            links[match.group(2)] = match.group(1)
    return links


def fetch_comments(comments_url: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    """Fetch all comments for an issue using Link header pagination."""
    comments: list[dict[str, Any]] = []
    per_page = 100

    params = {"per_page": per_page}
    next_url: str | None = comments_url

    while next_url:
        response = requests.get(next_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        if not data:
            break

        comments.extend(data)

        # Use Link header for cursor-based pagination
        links = parse_link_header(response.headers.get("Link"))
        next_url = links.get("next")

        # Clear params for subsequent requests
        params = {}

    return comments


def download_issues(
    owner: str, repo: str, limit: int | None = None
) -> list[dict[str, Any]]:
    """Download all issues and their comments from a GitHub repository."""
    headers = get_github_headers()
    issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues"

    limit_str = f" (limit: {limit})" if limit else ""
    print(f"Fetching issues from {owner}/{repo}{limit_str}...", file=sys.stderr)

    # Fetch issues, filtering out PRs as we go to respect the limit correctly
    issues: list[dict[str, Any]] = []
    per_page = 100
    params: dict[str, Any] = {"per_page": per_page, "state": "all"}
    next_url: str | None = issues_url

    while next_url:
        response = requests.get(next_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        if not data:
            break

        # Filter out pull requests as we fetch
        for item in data:
            if "pull_request" not in item:
                issues.append(item)
                if limit and len(issues) >= limit:
                    break

        # Check if we've reached the limit
        if limit and len(issues) >= limit:
            break

        # Use Link header for cursor-based pagination
        links = parse_link_header(response.headers.get("Link"))
        next_url = links.get("next")
        params = {}

    print(f"Found {len(issues)} issues. Fetching comments...", file=sys.stderr)

    # Fetch comments for each issue
    for i, issue in enumerate(issues):
        if issue.get("comments", 0) > 0:
            comments_url = issue["comments_url"]
            issue["comments_data"] = fetch_comments(comments_url, headers)
        else:
            issue["comments_data"] = []

        # Progress indicator
        if (i + 1) % 10 == 0 or i + 1 == len(issues):
            print(f"  Processed {i + 1}/{len(issues)} issues", file=sys.stderr)

    return issues


def parse_repo_string(repo_string: str) -> tuple[str, str]:
    """Parse a repository string in the format 'owner/repo'."""
    parts = repo_string.split("/")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid repository format: {repo_string}. Expected 'owner/repo'"
        )
    return parts[0], parts[1]


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the issue analyzer."""
    parser = argparse.ArgumentParser(
        description="Download all GitHub issues from a repository to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    ./issue_analyzer.py rancher/dartboard
    ./issue_analyzer.py rancher/dartboard issues.json
    ./issue_analyzer.py --limit 100 rancher/rancher

Set GITHUB_TOKEN env var for higher rate limits.
        """,
    )
    parser.add_argument(
        "repository",
        help="GitHub repository in 'owner/repo' format",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output JSON file (default: <repo>_issues.json)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Maximum number of issues to download (default: all)",
    )

    args = parser.parse_args(argv)

    try:
        owner, repo = parse_repo_string(args.repository)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output_file = args.output or f"{repo}_issues.json"

    try:
        issues = download_issues(owner, repo, limit=args.limit)
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching issues: {e}", file=sys.stderr)
        return 1
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        return 1

    # Write to JSON file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(issues)} issues to {output_file}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
