"""Tests for collecting a report with a JST activity window."""

from datetime import date
from unittest.mock import patch

from src.config.settings import Settings
from src.services.collector import DataCollector


class TestDataCollector:
    def test_collect_passes_previous_jst_day_to_every_activity_query(self) -> None:
        settings = Settings(
            gh_token="token",
            github_target_type="repos",
            github_target_repos="owner/repo",
        )
        with patch("src.services.collector.GitHubClient") as client_type:
            client = client_type.return_value
            client.get_repo_prs.return_value = []
            client.get_repo_issues.return_value = []
            client.get_repo_commits.return_value = []

            DataCollector(settings).collect(date(2026, 6, 29))

        expected_since = "2026-06-28T15:00:00Z"
        expected_until = "2026-06-29T15:00:00Z"
        client.get_repo_prs.assert_called_once_with(
            "owner", "repo", expected_since, expected_until
        )
        client.get_repo_issues.assert_called_once_with(
            "owner", "repo", expected_since, expected_until
        )
        client.get_repo_commits.assert_called_once_with(
            "owner", "repo", expected_since, expected_until
        )
