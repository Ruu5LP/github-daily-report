"""Markdown report generator."""

from __future__ import annotations

from collections import defaultdict

from src.models.report import Commit, DailyReport, Issue, PullRequest


def generate_report(report: DailyReport) -> str:
    """Generate a full Markdown report string."""
    lines: list[str] = []

    date_str = report.date.strftime("%Y-%m-%d")
    lines.append(f"# 開発日報 {date_str}")
    lines.append("")

    # --- Overall Summary ---
    lines.append("## 全体サマリ")
    lines.append("")
    lines.append(f"- 更新Repositoryの数: {len(report.updated_repos)}")
    lines.append(f"- 作成PR: {len(report.created_prs)}")
    lines.append(f"- Merge PR: {len(report.merged_prs)}")
    lines.append(f"- Close Issue: {len(report.closed_issues)}")
    lines.append(f"- Commit数: {len(report.commits)}")
    lines.append(f"- Review待ちPR: {len(report.review_waiting_prs)}")
    lines.append("")

    # --- Per-user progress ---
    lines.append("## 人別進捗")
    lines.append("")

    users = _collect_users(report)
    for user in sorted(users):
        lines.extend(_user_section(user, report))

    # --- Per-repo summary ---
    lines.append("## Repository別")
    lines.append("")

    repos = sorted(report.updated_repos)
    for repo in repos:
        lines.extend(_repo_section(repo, report))

    return "\n".join(lines)


def _collect_users(report: DailyReport) -> set[str]:
    users: set[str] = set()
    for pr in report.pull_requests:
        users.add(pr.author)
        users.update(pr.requested_reviewers)
    for issue in report.closed_issues:
        users.add(issue.author)
    for commit in report.commits:
        users.add(commit.author)
    return users


def _user_section(user: str, report: DailyReport) -> list[str]:
    lines: list[str] = []
    lines.append(f"### {user}")
    lines.append("")

    created = [pr for pr in report.created_prs if pr.author == user]
    merged = [pr for pr in report.merged_prs if pr.author == user]
    closed_issues = [i for i in report.closed_issues if i.author == user]
    commits = [c for c in report.commits if c.author == user]
    review_waiting = [pr for pr in report.review_waiting_prs if user in pr.requested_reviewers]

    # Skip users with no activity
    if not any([created, merged, closed_issues, commits, review_waiting]):
        return []

    if created:
        lines.append("#### 作成PR")
        for pr in created:
            lines.append(f"- {_pr_link(pr)} @ {pr.repo}")
        lines.append("")

    if merged:
        lines.append("#### MergePR")
        for pr in merged:
            lines.append(f"- {_pr_link(pr)} @ {pr.repo}")
        lines.append("")

    if closed_issues:
        lines.append("#### CloseIssue")
        for issue in closed_issues:
            lines.append(f"- {_issue_link(issue)} @ {issue.repo}")
        lines.append("")

    if commits:
        lines.append("#### Commit")
        for commit in commits:
            lines.append(f"- {commit.short_sha}: {commit.first_line} @ {commit.repo}")
        lines.append("")

    if review_waiting:
        lines.append("#### Review待ち")
        for pr in review_waiting:
            requesters = [r for r in pr.requested_reviewers if r != user]
            requested_by = f" (requested by: {', '.join(requesters)})" if requesters else ""
            lines.append(f"- {_pr_link(pr)} @ {pr.repo}{requested_by}")
        lines.append("")

    return lines


def _repo_section(repo: str, report: DailyReport) -> list[str]:
    lines: list[str] = []
    lines.append(f"### {repo}")
    lines.append("")

    repo_prs = [pr for pr in report.pull_requests if pr.repo == repo]
    repo_issues = [i for i in report.closed_issues if i.repo == repo]
    repo_commits = [c for c in report.commits if c.repo == repo]

    if repo_prs:
        lines.append("#### PR")
        for pr in repo_prs:
            status = pr.state
            lines.append(f"- {_pr_link(pr)} - {status}")
        lines.append("")

    if repo_issues:
        lines.append("#### Issue")
        for issue in repo_issues:
            lines.append(f"- {_issue_link(issue)} - closed")
        lines.append("")

    if repo_commits:
        lines.append("#### Commit")
        for commit in repo_commits:
            lines.append(f"- {commit.short_sha}: {commit.first_line} (by: {commit.author})")
        lines.append("")

    return lines


def _pr_link(pr: PullRequest) -> str:
    return f"[#{pr.number} {pr.title}]({pr.url})"


def _issue_link(issue: Issue) -> str:
    return f"[#{issue.number} {issue.title}]({issue.url})"


# --- Per-user grouping helpers (used by notification) ---


def group_by_user(report: DailyReport) -> dict[str, dict[str, list[PullRequest | Issue | Commit]]]:
    """Group report data by user for notification purposes."""
    result: dict[str, dict[str, list[PullRequest | Issue | Commit]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for pr in report.created_prs:
        result[pr.author]["created_prs"].append(pr)
    for pr in report.merged_prs:
        result[pr.author]["merged_prs"].append(pr)
    for issue in report.closed_issues:
        result[issue.author]["closed_issues"].append(issue)
    for commit in report.commits:
        result[commit.author]["commits"].append(commit)
    for pr in report.review_waiting_prs:
        for reviewer in pr.requested_reviewers:
            result[reviewer]["review_waiting"].append(pr)
    return dict(result)
