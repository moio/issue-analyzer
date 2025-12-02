#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Issue Summarizer - Export GitHub issues from SQLite database to JSON.

This script reads issues (including comments) from a SQLite database created by
issue_downloader.py and exports them to a JSON file for analysis.

Usage:
    ./issue_summarizer.py <input.db> [output.json]

Examples:
    ./issue_summarizer.py dartboard_issues.db
    ./issue_summarizer.py dartboard_issues.db issues.json
"""

import argparse
import json
import sqlite3
import sys
from typing import Any


def export_database_to_json(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Export all issues and comments from the database to a list of dicts."""
    issues: list[dict[str, Any]] = []

    cursor = conn.execute("SELECT number, data FROM issues ORDER BY number DESC")
    for row in cursor.fetchall():
        issue_number, issue_data = row
        issue = json.loads(issue_data)

        # Fetch comments for this issue
        comments_cursor = conn.execute(
            "SELECT data FROM comments WHERE issue_number = ? ORDER BY id",
            (issue_number,),
        )
        comments = [json.loads(c[0]) for c in comments_cursor.fetchall()]
        issue["comments_data"] = comments

        issues.append(issue)

    return issues


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the issue summarizer."""
    parser = argparse.ArgumentParser(
        description="Export GitHub issues from SQLite database to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    ./issue_summarizer.py dartboard_issues.db
    ./issue_summarizer.py dartboard_issues.db issues.json

The input database should be created by issue_downloader.py.
        """,
    )
    parser.add_argument(
        "input",
        help="Input SQLite database file",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output JSON file (default: replaces .db extension with .json)",
    )

    args = parser.parse_args(argv)

    db_path = args.input

    # Derive default output file from input database name
    if args.output:
        output_file = args.output
    else:
        # Remove .db extension and add _issues.json
        if db_path.endswith(".db"):
            output_file = db_path[:-3] + ".json"
        else:
            output_file = db_path + ".json"

    try:
        conn = sqlite3.connect(db_path)
        # Check if database has the expected tables
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='issues'"
        )
        if not cursor.fetchone():
            print(
                f"Error: {db_path} does not contain an 'issues' table", file=sys.stderr
            )
            return 1

        issues = export_database_to_json(conn)
        conn.close()
    except sqlite3.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        return 1

    # Write to JSON file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(issues)} issues to {output_file}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
