"""Markdown report generator."""

from __future__ import annotations

from collections import defaultdict

from src.models.report import Commit, DailyReport, Issue, PullRequest

DIVIDER = "─" * 36


def generate_report(report: DailyReport) -> str:
    """Generate a Discord-friendly report string."""
    blocks: list[str] = []

    date_str = report.date.strftime("%Y-%m-%d")

    # --- Header + Summary ---
    blocks.append(
        "\n".join(
            [
                f"📋 **開発日報 {date_str}**",
                "",
                "**今日のまとめ**",
                f"　リポジトリ更新: **{len(report.updated_repos)}**",
                f"　PR作成: **{len(report.created_prs)}**　／　Merge: **{len(report.merged_prs)}**",
                f"　Issue完了: **{len(report.closed_issues)}**",
                f"　今日のCommit: **{len(report.commits)}**",
                f"　Review待ち: **{len(report.review_waiting_prs)}**",
            ]
        )
    )

    # --- Per-user progress ---
    users = _collect_users(report)
    user_blocks = [_user_section(user, report) for user in sorted(users)]
    user_blocks = [b for b in user_blocks if b]

    if user_blocks:
        blocks.append(f"{DIVIDER}\n**メンバーの動き**")
        for block in user_blocks:
            blocks.append(block)

    # --- Per-repo summary ---
    repos = sorted(report.updated_repos)
    repo_blocks = [_repo_section(repo, report) for repo in repos]

    if repo_blocks:
        blocks.append(f"{DIVIDER}\n**📁 Repository別**")
        for block in repo_blocks:
            blocks.append(block)

    return "\n\n".join(blocks)


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


def _user_section(user: str, report: DailyReport) -> str:
    created = [pr for pr in report.created_prs if pr.author == user]
    merged = [pr for pr in report.merged_prs if pr.author == user]
    closed_issues = [i for i in report.closed_issues if i.author == user]
    commits = [c for c in report.commits if c.author == user]
    review_waiting = [pr for pr in report.review_waiting_prs if user in pr.requested_reviewers]

    if not any([created, merged, closed_issues, commits, review_waiting]):
        return ""

    lines = [f"👤 **{user}**"]

    if created:
        lines.append("")
        lines.append("  **作成PR**")
        for pr in created:
            lines.append(f"  • `{_short_repo(pr.repo)}` {_pr_link(pr)}")

    if merged:
        lines.append("")
        lines.append("  **MergePR**")
        for pr in merged:
            lines.append(f"  • `{_short_repo(pr.repo)}` {_pr_link(pr)}")

    if closed_issues:
        lines.append("")
        lines.append("  **CloseIssue**")
        for issue in closed_issues:
            lines.append(f"  • `{_short_repo(issue.repo)}` {_issue_link(issue)}")

    if commits:
        lines.append("")
        lines.append(f"  **今日のCommit** ({len(commits)}件)")
        for commit in commits[:5]:
            repo_name = _short_repo(commit.repo)
            lines.append(f"  • `{repo_name}` `{commit.short_sha}` {commit.first_line}")
        if len(commits) > 5:
            lines.append(f"  • ...他 {len(commits) - 5} 件")

    if review_waiting:
        lines.append("")
        lines.append("  **Review待ち**")
        for pr in review_waiting:
            lines.append(f"  • `{_short_repo(pr.repo)}` {_pr_link(pr)}")

    return "\n".join(lines)


def _repo_section(repo: str, report: DailyReport) -> str:
    repo_prs = [pr for pr in report.pull_requests if pr.repo == repo]
    repo_issues = [i for i in report.closed_issues if i.repo == repo]
    repo_commits = [c for c in report.commits if c.repo == repo]

    lines = [f"**`{_short_repo(repo)}`**"]

    if repo_prs:
        open_prs = [p for p in repo_prs if p.state == "open"]
        merged_prs = [p for p in repo_prs if p.state == "merged"]
        closed_prs = [p for p in repo_prs if p.state == "closed"]
        pr_parts = []
        if open_prs:
            pr_parts.append(f"open {len(open_prs)}")
        if merged_prs:
            pr_parts.append(f"merged {len(merged_prs)}")
        if closed_prs:
            pr_parts.append(f"closed {len(closed_prs)}")
        lines.append("")
        lines.append(f"  **PR** ({' / '.join(pr_parts)})")
        for pr in repo_prs:
            label = {"open": "open", "merged": "merged", "closed": "closed"}.get(pr.state, pr.state)
            lines.append(f"  • [{label}] {_pr_link(pr)}")

    if repo_issues:
        lines.append("")
        lines.append(f"  **Issue** ({len(repo_issues)}件 closed)")
        for issue in repo_issues:
            lines.append(f"  • {_issue_link(issue)}")

    if repo_commits:
        lines.append("")
        lines.append(f"  **今日のCommit** ({len(repo_commits)}件)")
        for commit in repo_commits[:5]:
            lines.append(f"  • `{commit.short_sha}` {commit.first_line} ({commit.author})")
        if len(repo_commits) > 5:
            lines.append(f"  • ...他 {len(repo_commits) - 5} 件")

    return "\n".join(lines)


def _pr_link(pr: PullRequest) -> str:
    return f"[#{pr.number} {pr.title}]({pr.url})"


def _issue_link(issue: Issue) -> str:
    return f"[#{issue.number} {issue.title}]({issue.url})"


def _short_repo(full_repo: str) -> str:
    """Return just the repo name part (without org prefix)."""
    return full_repo.split("/")[-1]


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
