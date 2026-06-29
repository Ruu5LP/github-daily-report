"""Tests for the Markdown report generator."""

from datetime import UTC, date, datetime

from src.models.report import Commit, DailyReport, Issue, PullRequest
from src.report.generator import generate_report

UTC = UTC
TODAY = date(2026, 6, 29)


def make_pr(
    number: int = 1,
    title: str = "Test PR",
    author: str = "alice",
    repo: str = "owner/repo",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    merged_at: datetime | None = None,
    state: str = "open",
    requested_reviewers: list[str] | None = None,
) -> PullRequest:
    dt = datetime(2026, 6, 29, 10, 0, 0, tzinfo=UTC)
    return PullRequest(
        number=number,
        title=title,
        url=f"https://github.com/owner/repo/pull/{number}",
        state=state,
        author=author,
        repo=repo,
        created_at=created_at or dt,
        updated_at=updated_at or dt,
        merged_at=merged_at,
        requested_reviewers=requested_reviewers or [],
    )


def make_issue(
    number: int = 10,
    title: str = "Test Issue",
    author: str = "bob",
    repo: str = "owner/repo",
    closed_at: datetime | None = None,
) -> Issue:
    dt = datetime(2026, 6, 29, 12, 0, 0, tzinfo=UTC)
    return Issue(
        number=number,
        title=title,
        url=f"https://github.com/owner/repo/issues/{number}",
        state="closed",
        author=author,
        repo=repo,
        closed_at=closed_at or dt,
    )


def make_commit(
    sha: str = "abc1234567",
    message: str = "fix: something",
    author: str = "alice",
    repo: str = "owner/repo",
    committed_at: datetime | None = None,
) -> Commit:
    dt = datetime(2026, 6, 29, 9, 0, 0, tzinfo=UTC)
    return Commit(
        sha=sha,
        message=message,
        author=author,
        url=f"https://github.com/owner/repo/commit/{sha}",
        repo=repo,
        committed_at=committed_at or dt,
    )


class TestDailyReportModel:
    def test_created_prs(self) -> None:
        pr = make_pr(created_at=datetime(2026, 6, 29, 5, 0, tzinfo=UTC))
        other_pr = make_pr(number=2, created_at=datetime(2026, 6, 28, 5, 0, tzinfo=UTC))
        report = DailyReport(date=TODAY, pull_requests=[pr, other_pr])
        assert len(report.created_prs) == 1
        assert report.created_prs[0].number == 1

    def test_merged_prs(self) -> None:
        merged_pr = make_pr(
            number=1,
            state="merged",
            merged_at=datetime(2026, 6, 29, 15, 0, tzinfo=UTC),
        )
        open_pr = make_pr(number=2)
        report = DailyReport(date=TODAY, pull_requests=[merged_pr, open_pr])
        assert len(report.merged_prs) == 1
        assert report.merged_prs[0].number == 1

    def test_review_waiting_prs(self) -> None:
        pr_with_review = make_pr(requested_reviewers=["bob"])
        pr_no_review = make_pr(number=2)
        report = DailyReport(date=TODAY, pull_requests=[pr_with_review, pr_no_review])
        assert len(report.review_waiting_prs) == 1
        assert report.review_waiting_prs[0].requested_reviewers == ["bob"]

    def test_closed_issues(self) -> None:
        issue_today = make_issue(closed_at=datetime(2026, 6, 29, 8, 0, tzinfo=UTC))
        issue_yesterday = make_issue(number=11, closed_at=datetime(2026, 6, 28, 8, 0, tzinfo=UTC))
        report = DailyReport(date=TODAY, issues=[issue_today, issue_yesterday])
        assert len(report.closed_issues) == 1
        assert report.closed_issues[0].number == 10

    def test_updated_repos(self) -> None:
        pr = make_pr(repo="owner/repo-a")
        issue = make_issue(repo="owner/repo-b", closed_at=datetime(2026, 6, 29, 1, 0, tzinfo=UTC))
        commit = make_commit(repo="owner/repo-c")
        report = DailyReport(date=TODAY, pull_requests=[pr], issues=[issue], commits=[commit])
        assert report.updated_repos == {"owner/repo-a", "owner/repo-b", "owner/repo-c"}


class TestGenerateReport:
    def test_header(self) -> None:
        report = DailyReport(date=TODAY)
        md = generate_report(report)
        assert "開発日報 2026-06-29" in md

    def test_summary_section(self) -> None:
        pr = make_pr(
            created_at=datetime(2026, 6, 29, 5, 0, tzinfo=UTC),
            state="merged",
            merged_at=datetime(2026, 6, 29, 15, 0, tzinfo=UTC),
        )
        issue = make_issue(closed_at=datetime(2026, 6, 29, 8, 0, tzinfo=UTC))
        commit = make_commit()
        report = DailyReport(date=TODAY, pull_requests=[pr], issues=[issue], commits=[commit])
        md = generate_report(report)
        assert "PR作成" in md
        assert "Merge" in md
        assert "Issue完了" in md
        assert "Commit" in md

    def test_user_section_appears(self) -> None:
        pr = make_pr(author="alice", created_at=datetime(2026, 6, 29, 5, 0, tzinfo=UTC))
        report = DailyReport(date=TODAY, pull_requests=[pr])
        md = generate_report(report)
        assert "alice" in md
        assert "作成PR" in md

    def test_review_waiting_shows_requested_by(self) -> None:
        pr = make_pr(
            author="alice",
            state="open",
            requested_reviewers=["bob", "carol"],
        )
        report = DailyReport(date=TODAY, pull_requests=[pr])
        md = generate_report(report)
        assert "Review待ち" in md

    def test_repo_section(self) -> None:
        pr = make_pr(repo="myorg/myrepo")
        report = DailyReport(date=TODAY, pull_requests=[pr])
        md = generate_report(report)
        assert "myrepo" in md

    def test_commit_short_sha(self) -> None:
        commit = make_commit(sha="deadbeef1234")
        report = DailyReport(date=TODAY, commits=[commit])
        md = generate_report(report)
        assert "deadbee" in md  # first 7 chars

    def test_empty_report(self) -> None:
        report = DailyReport(date=TODAY)
        md = generate_report(report)
        assert "開発日報" in md
        assert "今日のまとめ" in md
