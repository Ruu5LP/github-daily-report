"""Data models for the daily report."""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class PullRequest:
    number: int
    title: str
    url: str
    state: str  # open, closed, merged
    author: str
    repo: str
    created_at: datetime
    updated_at: datetime
    merged_at: datetime | None
    requested_reviewers: list[str] = field(default_factory=list)

    @property
    def is_merged(self) -> bool:
        return self.merged_at is not None

    @property
    def short_sha_url(self) -> str:
        return f"[#{self.number} {self.title}]({self.url})"


@dataclass
class Issue:
    number: int
    title: str
    url: str
    state: str  # open, closed
    author: str
    repo: str
    closed_at: datetime | None

    @property
    def short_url(self) -> str:
        return f"[#{self.number} {self.title}]({self.url})"


@dataclass
class Commit:
    sha: str
    message: str
    author: str
    url: str
    repo: str
    committed_at: datetime

    @property
    def short_sha(self) -> str:
        return self.sha[:7]

    @property
    def first_line(self) -> str:
        return self.message.splitlines()[0] if self.message else ""


@dataclass
class DailyReport:
    date: date
    pull_requests: list[PullRequest] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    commits: list[Commit] = field(default_factory=list)

    @property
    def created_prs(self) -> list[PullRequest]:
        d = self.date
        return [pr for pr in self.pull_requests if pr.created_at.date() == d]

    @property
    def merged_prs(self) -> list[PullRequest]:
        d = self.date
        return [
            pr for pr in self.pull_requests if pr.merged_at is not None and pr.merged_at.date() == d
        ]

    @property
    def updated_prs(self) -> list[PullRequest]:
        """PRs updated today but not created or merged today."""
        d = self.date
        created = {pr.number for pr in self.created_prs}
        merged = {pr.number for pr in self.merged_prs}
        return [
            pr
            for pr in self.pull_requests
            if pr.updated_at.date() == d and pr.number not in created and pr.number not in merged
        ]

    @property
    def review_waiting_prs(self) -> list[PullRequest]:
        return [pr for pr in self.pull_requests if pr.requested_reviewers and pr.state == "open"]

    @property
    def closed_issues(self) -> list[Issue]:
        d = self.date
        return [
            issue
            for issue in self.issues
            if issue.closed_at is not None and issue.closed_at.date() == d
        ]

    @property
    def updated_repos(self) -> set[str]:
        repos: set[str] = set()
        for pr in self.pull_requests:
            repos.add(pr.repo)
        for issue in self.issues:
            repos.add(issue.repo)
        for commit in self.commits:
            repos.add(commit.repo)
        return repos
