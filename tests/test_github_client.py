"""Tests for GitHub API date windows."""

from datetime import UTC, datetime
from unittest.mock import patch

from src.github.client import GitHubClient

SINCE = "2026-06-28T15:00:00Z"
UNTIL = "2026-06-29T15:00:00Z"


def make_commit_item(sha: str, committed_at: str, message: str = "commit") -> dict[str, object]:
    return {
        "sha": sha,
        "html_url": f"https://github.com/owner/repo/commit/{sha}",
        "commit": {
            "message": message,
            "author": {"name": "alice", "date": committed_at},
        },
    }


class TestGitHubClientDateWindows:
    def test_pr_search_uses_utc_timestamp_window(self) -> None:
        client = GitHubClient("token")
        with (
            patch.object(client, "_search_issues", return_value=[]) as search,
            patch.object(client, "_get_open_prs", return_value=[]),
        ):
            client.get_repo_prs("owner", "repo", SINCE, UNTIL)

        search.assert_called_once_with(
            "type:pr repo:owner/repo updated:>=2026-06-28T15:00:00Z updated:<2026-06-29T15:00:00Z"
        )

    def test_issue_search_uses_utc_timestamp_window(self) -> None:
        client = GitHubClient("token")
        with patch.object(client, "_search_issues", return_value=[]) as search:
            client.get_repo_issues("owner", "repo", SINCE, UNTIL)

        search.assert_called_once_with(
            "type:issue repo:owner/repo is:closed "
            "closed:>=2026-06-28T15:00:00Z closed:<2026-06-29T15:00:00Z"
        )

    def test_default_branch_commits_use_half_open_window(self) -> None:
        client = GitHubClient("token")
        items = [
            make_commit_item("before", "2026-06-28T14:59:59Z"),
            make_commit_item("start", "2026-06-28T15:00:00Z"),
            make_commit_item("end", "2026-06-29T15:00:00Z"),
        ]
        with patch.object(client, "_paginate", return_value=items) as paginate:
            commits = client.get_repo_commits("owner", "repo", SINCE, UNTIL)

        assert [commit.sha for commit in commits] == ["start"]
        assert paginate.call_args.kwargs["params"] == {
            "since": "2026-06-28T14:59:59Z",
            "until": UNTIL,
        }

    def test_default_branch_commit_query_normalizes_offset_to_utc(self) -> None:
        client = GitHubClient("token")
        with patch.object(client, "_paginate", return_value=[]) as paginate:
            client.get_repo_commits(
                "owner",
                "repo",
                "2026-06-29T00:00:00+09:00",
                "2026-06-30T00:00:00+09:00",
            )

        assert paginate.call_args.kwargs["params"] == {
            "since": "2026-06-28T14:59:59Z",
            "until": "2026-06-29T15:00:00Z",
        }

    def test_pr_commits_use_half_open_window(self) -> None:
        client = GitHubClient("token")
        items = [
            make_commit_item("start", "2026-06-28T15:00:00Z"),
            make_commit_item("end", "2026-06-29T15:00:00Z"),
        ]
        with patch.object(client, "_paginate", return_value=items):
            commits = client.get_pr_commits("owner", "repo", 1, SINCE, UNTIL)

        assert [commit.sha for commit in commits] == ["start"]

    def test_commit_items_with_timezone_offsets_are_compared_as_datetimes(self) -> None:
        client = GitHubClient("token")
        items = [make_commit_item("start", "2026-06-29T00:00:00+09:00")]
        with patch.object(client, "_paginate", return_value=items):
            commits = client.get_pr_commits("owner", "repo", 1, SINCE, UNTIL)

        assert commits[0].committed_at == datetime(2026, 6, 28, 15, 0, tzinfo=UTC)
