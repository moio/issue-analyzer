#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31.0",
# ]
# ///
"""
Issue Downloader - Download all GitHub issues from a repository to SQLite.

This script downloads all issues (including comments) from a GitHub repository
and saves them to a SQLite database for later analysis.

Data is stored in a SQLite database as it is fetched, providing resilience
against network errors and power loss. On restart, the script resumes from
where it left off, skipping issues already in the database.

Note: Issues already in the database are not refreshed on subsequent runs.
To get fresh data, delete the database file (<repo>_issues.db).

Usage:
    ./issue_downloader.py <owner>/<repo> [output.db]

Examples:
    ./issue_downloader.py rancher/dartboard
    ./issue_downloader.py rancher/dartboard issues.db
    ./issue_downloader.py --limit 100 rancher/rancher
    ./issue_downloader.py --rate-limit 1000 rancher/rancher

Environment variables:
    GITHUB_TOKEN: Set for higher rate limits (create at https://github.com/settings/tokens)
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from typing import Any

import requests

# Retry configuration
MAX_RETRIES = 10
INITIAL_BACKOFF = 1  # seconds

# Rate limiting configuration
DEFAULT_RATE_LIMIT = 5000  # requests per hour (GitHub default for authenticated users)
RATE_LIMIT_USAGE_FRACTION = 0.9  # Use only 90% of the rate limit


class RateLimiter:
    """Rate limiter that tracks request timing and adds delays to stay within limits."""

    def __init__(self, requests_per_hour: int) -> None:
        """Initialize the rate limiter.

        Args:
            requests_per_hour: Maximum requests allowed per hour.
        """
        # Apply 90% safety margin
        effective_limit = int(requests_per_hour * RATE_LIMIT_USAGE_FRACTION)
        self.min_interval = 3600.0 / effective_limit  # seconds between requests
        self.last_request_time: float | None = None

    def wait_if_needed(self) -> None:
        """Wait if necessary to stay within rate limits."""
        if self.last_request_time is None:
            self.last_request_time = time.time()
            return

        elapsed = time.time() - self.last_request_time
        wait_time = self.min_interval - elapsed

        if wait_time > 0:
            time.sleep(wait_time)

        self.last_request_time = time.time()


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


def request_with_retry(
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    timeout: int = 30,
    rate_limiter: RateLimiter | None = None,
) -> requests.Response:
    """Make an HTTP GET request with exponential backoff retry on errors.

    Retries up to MAX_RETRIES times on HTTP errors and network errors,
    with exponential backoff between retries. Logs full response body on errors.
    """
    last_exception: Exception | None = None
    backoff = INITIAL_BACKOFF

    for attempt in range(MAX_RETRIES):
        try:
            if rate_limiter:
                rate_limiter.wait_if_needed()

            response = requests.get(
                url, headers=headers, params=params, timeout=timeout
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            last_exception = e
            response_body = ""
            try:
                response_body = e.response.text if e.response is not None else ""
            except Exception:
                response_body = "<unable to read response body>"

            print(
                f"HTTP error on attempt {attempt + 1}/{MAX_RETRIES}: {e}",
                file=sys.stderr,
            )
            print(f"Response body: {response_body}", file=sys.stderr)

            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {backoff} seconds...", file=sys.stderr)
                time.sleep(backoff)
                backoff *= 2
        except requests.exceptions.RequestException as e:
            last_exception = e
            print(
                f"Network error on attempt {attempt + 1}/{MAX_RETRIES}: {e}",
                file=sys.stderr,
            )

            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {backoff} seconds...", file=sys.stderr)
                time.sleep(backoff)
                backoff *= 2

    # All retries exhausted
    raise last_exception  # type: ignore[misc]


def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize the SQLite database with the required schema."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY,
            number INTEGER UNIQUE NOT NULL,
            data TEXT NOT NULL
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY,
            issue_number INTEGER NOT NULL,
            data TEXT NOT NULL,
            FOREIGN KEY (issue_number) REFERENCES issues(number)
        )
    """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_comments_issue_number
        ON comments(issue_number)
    """
    )
    conn.commit()
    return conn


def get_existing_issue_numbers(conn: sqlite3.Connection) -> set[int]:
    """Get the set of issue numbers already in the database."""
    cursor = conn.execute("SELECT number FROM issues")
    return {row[0] for row in cursor.fetchall()}


def save_issue_with_comments(
    conn: sqlite3.Connection,
    issue: dict[str, Any],
    comments: list[dict[str, Any]],
) -> None:
    """Save an issue and its comments to the database in a single transaction."""
    issue_number = issue["number"]
    issue_id = issue["id"]

    # Create a copy of the issue without comments_data for storage
    issue_data = {k: v for k, v in issue.items() if k != "comments_data"}

    conn.execute("BEGIN")
    try:
        conn.execute(
            "INSERT OR REPLACE INTO issues (id, number, data) VALUES (?, ?, ?)",
            (issue_id, issue_number, json.dumps(issue_data, ensure_ascii=False)),
        )
        # Delete existing comments for this issue (in case of resume with partial data)
        conn.execute("DELETE FROM comments WHERE issue_number = ?", (issue_number,))
        for comment in comments:
            conn.execute(
                "INSERT INTO comments (id, issue_number, data) VALUES (?, ?, ?)",
                (comment["id"], issue_number, json.dumps(comment, ensure_ascii=False)),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def fetch_comments(comments_url: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    """Fetch all comments for an issue using Link header pagination."""
    comments: list[dict[str, Any]] = []
    per_page = 100

    params: dict[str, Any] = {"per_page": per_page}
    next_url: str | None = comments_url

    while next_url:
        response = request_with_retry(
            next_url, headers, params=params, rate_limiter=rate_limiter
        )

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
    owner: str,
    repo: str,
    db_path: str,
    limit: int | None = None,
    rate_limit: int = DEFAULT_RATE_LIMIT,
) -> list[dict[str, Any]]:
    """Download all issues and their comments from a GitHub repository.

    Uses SQLite database for persistence. On restart, skips issues already
    in the database.

    Returns the total number of issues in the database after downloading.
    """
    headers = get_github_headers()
    issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    rate_limiter = RateLimiter(rate_limit)

    # Initialize database and get existing issues
    conn = init_database(db_path)
    existing_issues = get_existing_issue_numbers(conn)

    if existing_issues:
        print(
            f"Resuming: found {len(existing_issues)} issues already in database",
            file=sys.stderr,
        )

    limit_str = f" (limit: {limit})" if limit else ""
    print(f"Fetching issues from {owner}/{repo}{limit_str}...", file=sys.stderr)

    # Fetch issues, filtering out PRs as we go to respect the limit correctly
    issues_to_process: list[dict[str, Any]] = []
    seen_issue_numbers: set[int] = set(existing_issues)
    per_page = 100
    params: dict[str, Any] = {"per_page": per_page, "state": "all"}
    next_url: str | None = issues_url

    while next_url:
        response = request_with_retry(
            next_url, headers, params=params, rate_limiter=rate_limiter
        )

        data = response.json()
        if not data:
            break

        # Filter out pull requests as we fetch
        for item in data:
            if "pull_request" not in item:
                issue_number = item["number"]
                if issue_number not in seen_issue_numbers:
                    issues_to_process.append(item)
                    seen_issue_numbers.add(issue_number)

                if limit and len(seen_issue_numbers) >= limit:
                    break

        # Check if we've reached the limit
        if limit and len(seen_issue_numbers) >= limit:
            break

        # Use Link header for cursor-based pagination
        links = parse_link_header(response.headers.get("Link"))
        next_url = links.get("next")
        params = {}

    new_issues_count = len(issues_to_process)
    if new_issues_count == 0:
        print("No new issues to fetch.", file=sys.stderr)
    else:
        print(
            f"Found {new_issues_count} new issues to fetch. Processing...",
            file=sys.stderr,
        )

    # Fetch comments for each new issue and save to database
    for i, issue in enumerate(issues_to_process):
        if issue.get("comments", 0) > 0:
            comments_url = issue["comments_url"]
            comments = fetch_comments(comments_url, headers, rate_limiter)
        else:
            comments = []

        # Save issue with comments in a single transaction
        save_issue_with_comments(conn, issue, comments)

        # Progress indicator
        if (i + 1) % 10 == 0 or i + 1 == new_issues_count:
            print(
                f"  Processed {i + 1}/{new_issues_count} new issues",
                file=sys.stderr,
            )

    # Get total count of issues in database
    cursor = conn.execute("SELECT COUNT(*) FROM issues")
    total_issues = cursor.fetchone()[0]
    conn.close()

    return total_issues


def parse_repo_string(repo_string: str) -> tuple[str, str]:
    """Parse a repository string in the format 'owner/repo'."""
    parts = repo_string.split("/")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid repository format: {repo_string}. Expected 'owner/repo'"
        )
    return parts[0], parts[1]


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the issue downloader."""
    parser = argparse.ArgumentParser(
        description="Download all GitHub issues from a repository to SQLite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    ./issue_downloader.py rancher/dartboard
    ./issue_downloader.py rancher/dartboard issues.db
    ./issue_downloader.py --limit 100 rancher/rancher
    ./issue_downloader.py --rate-limit 1000 rancher/rancher

Set GITHUB_TOKEN env var for higher rate limits.

Data is stored in a SQLite database (<repo>_issues.db) as it is fetched.
On restart, the script resumes from where it left off.
Note: Issues already in the database are not refreshed.
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
        help="Output SQLite database file (default: <repo>_issues.db)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Maximum number of issues to download (default: all)",
    )
    parser.add_argument(
        "--rate-limit",
        "-r",
        type=int,
        default=DEFAULT_RATE_LIMIT,
        help=f"Maximum requests per hour (default: {DEFAULT_RATE_LIMIT}). "
        "Actual usage is limited to 90%% of this value.",
    )

    args = parser.parse_args(argv)

    try:
        owner, repo = parse_repo_string(args.repository)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    db_path = args.output or f"{repo}_issues.db"

    try:
        issues = download_issues(
            owner, repo, db_path, limit=args.limit, rate_limit=args.rate_limit
        )
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching issues: {e}", file=sys.stderr)
        return 1
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        return 1

    print(f"Database {db_path} contains {len(issues)} issues", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
