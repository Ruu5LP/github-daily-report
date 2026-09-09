"""Data collection service — orchestrates GitHub API calls."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from src.config.settings import Settings, TargetType
from src.github.client import GitHubClient
from src.models.report import Commit, DailyReport, PullRequest
from src.utils.logger import logger
from src.utils.time import JST


def _day_range(target_date: date) -> tuple[str, str]:
    """Return the UTC bounds for the full target day in Japan Standard Time."""
    # GitHub accepts UTC timestamps, while the report's business day is JST.
    # The interval is [target date 00:00 JST, next date 00:00 JST).
    jst_start = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        0,
        0,
        0,
        tzinfo=JST,
    )
    jst_end = jst_start + timedelta(days=1)
    since = jst_start.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    until = jst_end.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return since, until


class DataCollector:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = GitHubClient(settings.gh_token)

    def collect(self, target_date: date) -> DailyReport:
        repos = self._resolve_repos()
        logger.info("Collecting data for %s repos on %s", len(repos), target_date)

        report = DailyReport(date=target_date)
        since, until = _day_range(target_date)

        for repo_full in repos:
            parts = repo_full.split("/", 1)
            if len(parts) != 2:
                logger.warning("Invalid repo format: %s", repo_full)
                continue
            owner, repo = parts
            logger.info("Processing %s", repo_full)

            try:
                prs = self._collect_prs(owner, repo, since, until)
                report.pull_requests.extend(prs)

                issues = self._client.get_repo_issues(owner, repo, since, until)
                report.issues.extend(issues)
                logger.info("  Issues closed: %d", len(issues))

                commits = self._collect_commits(owner, repo, prs, since, until)
                report.commits.extend(commits)
                logger.info("  Commits: %d", len(commits))

            except Exception as e:
                logger.error("Error processing %s: %s", repo_full, e)

        return report

    def _collect_commits(
        self,
        owner: str,
        repo: str,
        prs: list[PullRequest],
        since: str,
        until: str,
    ) -> list[Commit]:
        """Collect target-day commits from default branch + active PRs (deduped by SHA)."""
        seen: set[str] = set()
        result: list[Commit] = []

        # Default branch commits
        for commit in self._client.get_repo_commits(owner, repo, since, until):
            if commit.sha not in seen:
                seen.add(commit.sha)
                result.append(commit)

        # Feature branch commits via PRs in the target-day activity window
        for pr in prs:
            for commit in self._client.get_pr_commits(owner, repo, pr.number, since, until):
                if commit.sha not in seen:
                    seen.add(commit.sha)
                    result.append(commit)

        return result

    def _collect_prs(self, owner: str, repo: str, since: str, until: str) -> list[PullRequest]:
        prs = self._client.get_repo_prs(owner, repo, since, until)
        # Enrich open PRs with requested reviewers via full PR endpoint
        enriched: list[PullRequest] = []
        for pr in prs:
            if pr.state == "open" and not pr.requested_reviewers:
                detailed = self._client.get_pr_details(owner, repo, pr.number)
                if detailed is not None:
                    enriched.append(detailed)
                    continue
            enriched.append(pr)

        logger.info(
            "  PRs: %d total (%d open with reviewers)",
            len(enriched),
            sum(1 for p in enriched if p.requested_reviewers),
        )
        return enriched

    def _resolve_repos(self) -> list[str]:
        target_type = self._settings.get_target_type()

        if target_type == TargetType.ORG_ALL:
            org = self._settings.github_target_org
            logger.info("Fetching all repos for org: %s", org)
            return self._client.get_org_repos(org)

        if target_type == TargetType.USER_ALL:
            user = self._settings.github_target_user
            logger.info("Fetching all repos for user: %s", user)
            return self._client.get_user_repos(user)

        # REPOS mode
        repos = self._settings.get_target_repos()
        logger.info("Using specified repos: %s", repos)
        return repos
