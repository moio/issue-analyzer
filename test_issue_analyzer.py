#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pytest>=7.0.0",
#     "requests>=2.31.0",
# ]
# ///
"""Unit tests for issue_analyzer.py."""

import json
from unittest.mock import MagicMock, patch

import pytest

# Import the module functions
from issue_analyzer import (
    download_issues,
    fetch_all_pages,
    fetch_comments,
    get_github_headers,
    main,
    parse_repo_string,
)


class TestGetGithubHeaders:
    """Tests for get_github_headers function."""

    def test_without_token(self):
        """Test headers without GITHUB_TOKEN set."""
        with patch.dict("os.environ", {}, clear=True):
            headers = get_github_headers()
            assert headers["Accept"] == "application/vnd.github.v3+json"
            assert headers["User-Agent"] == "issue-analyzer"
            assert "Authorization" not in headers

    def test_with_token(self):
        """Test headers with GITHUB_TOKEN set."""
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            headers = get_github_headers()
            assert headers["Authorization"] == "token test_token"


class TestParseRepoString:
    """Tests for parse_repo_string function."""

    def test_valid_repo_string(self):
        """Test parsing a valid repository string."""
        owner, repo = parse_repo_string("rancher/dartboard")
        assert owner == "rancher"
        assert repo == "dartboard"

    def test_invalid_repo_string_no_slash(self):
        """Test parsing an invalid repository string without slash."""
        with pytest.raises(ValueError) as exc_info:
            parse_repo_string("invalid")
        assert "Invalid repository format" in str(exc_info.value)

    def test_invalid_repo_string_too_many_slashes(self):
        """Test parsing an invalid repository string with too many slashes."""
        with pytest.raises(ValueError) as exc_info:
            parse_repo_string("owner/repo/extra")
        assert "Invalid repository format" in str(exc_info.value)


class TestFetchAllPages:
    """Tests for fetch_all_pages function."""

    def test_single_page(self):
        """Test fetching a single page of results."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1}, {"id": 2}]
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            results = fetch_all_pages("https://api.github.com/test", {})
            assert len(results) == 2
            assert results[0]["id"] == 1

    def test_multiple_pages(self):
        """Test fetching multiple pages of results."""
        page1 = [{"id": i} for i in range(100)]  # Full page
        page2 = [{"id": i} for i in range(100, 150)]  # Partial page

        mock_response1 = MagicMock()
        mock_response1.json.return_value = page1
        mock_response1.raise_for_status = MagicMock()

        mock_response2 = MagicMock()
        mock_response2.json.return_value = page2
        mock_response2.raise_for_status = MagicMock()

        with patch("requests.get", side_effect=[mock_response1, mock_response2]):
            results = fetch_all_pages("https://api.github.com/test", {})
            assert len(results) == 150


class TestFetchComments:
    """Tests for fetch_comments function."""

    def test_fetch_comments(self):
        """Test fetching comments for an issue."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": 1, "body": "Comment 1"},
            {"id": 2, "body": "Comment 2"},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            comments = fetch_comments("https://api.github.com/issues/1/comments", {})
            assert len(comments) == 2
            assert comments[0]["body"] == "Comment 1"


class TestDownloadIssues:
    """Tests for download_issues function."""

    def test_download_issues_filters_prs(self):
        """Test that pull requests are filtered out from issues."""
        issues_data = [
            {"id": 1, "number": 1, "comments": 0, "comments_url": "http://test/1"},
            {
                "id": 2,
                "number": 2,
                "comments": 0,
                "pull_request": {},
                "comments_url": "http://test/2",
            },  # PR
            {"id": 3, "number": 3, "comments": 0, "comments_url": "http://test/3"},
        ]

        mock_issues_response = MagicMock()
        mock_issues_response.json.return_value = issues_data
        mock_issues_response.raise_for_status = MagicMock()

        mock_empty_response = MagicMock()
        mock_empty_response.json.return_value = []
        mock_empty_response.raise_for_status = MagicMock()

        with patch(
            "requests.get", side_effect=[mock_issues_response, mock_empty_response]
        ):
            issues = download_issues("owner", "repo")
            # Should only have 2 issues (PR filtered out)
            assert len(issues) == 2
            assert all("pull_request" not in issue for issue in issues)


class TestMain:
    """Tests for main function."""

    def test_main_invalid_repo_format(self):
        """Test main with invalid repository format."""
        result = main(["invalid-repo-format"])
        assert result == 1

    def test_main_success(self, tmp_path):
        """Test successful execution of main."""
        output_file = tmp_path / "test_output.json"

        mock_issues = [
            {
                "id": 1,
                "number": 1,
                "title": "Test Issue",
                "comments": 0,
                "comments_url": "http://test",
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_issues
        mock_response.raise_for_status = MagicMock()

        mock_empty = MagicMock()
        mock_empty.json.return_value = []
        mock_empty.raise_for_status = MagicMock()

        with patch("requests.get", side_effect=[mock_response, mock_empty]):
            result = main(["owner/repo", str(output_file)])
            assert result == 0
            assert output_file.exists()

            with open(output_file) as f:
                data = json.load(f)
            assert len(data) == 1
            assert data[0]["title"] == "Test Issue"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
