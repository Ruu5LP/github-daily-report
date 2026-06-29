"""GitHub REST API client — centralized access layer."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import requests

from src.models.report import Commit, Issue, PullRequest
from src.utils.logger import logger

GITHUB_API_BASE = "https://api.github.com"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _require_datetime(value: str | None) -> datetime:
    result = _parse_datetime(value)
    if result is None:
        raise ValueError(f"Expected a datetime string, got {value!r}")
    return result


class RateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(self, reset_at: datetime) -> None:
        self.reset_at = reset_at
        super().__init__(f"Rate limit exceeded. Resets at {reset_at.isoformat()}")


class GitHubClient:
    def __init__(self, token: str) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        retries: int = 3,
    ) -> Any:
        url = f"{GITHUB_API_BASE}{path}"
        for attempt in range(retries):
            response = self._session.request(method, url, params=params)
            self._check_rate_limit(response)

            if response.status_code == 200:
                return response.json()

            if response.status_code in (403, 429) and (
                "rate limit" in response.text.lower() or response.status_code == 429
            ):
                reset_ts = int(response.headers.get("X-RateLimit-Reset", time.time() + 65))
                reset_at = datetime.fromtimestamp(reset_ts, tz=UTC)
                wait_secs = max(0, (reset_at - datetime.now(UTC)).total_seconds()) + 2
                if attempt < retries - 1:
                    logger.warning(
                        "Rate limit hit, waiting %.0fs until reset at %s",
                        wait_secs,
                        reset_at.isoformat(),
                    )
                    time.sleep(wait_secs)
                    continue
                raise RateLimitError(reset_at)

            if response.status_code in (500, 502, 503) and attempt < retries - 1:
                wait = 2**attempt
                logger.warning("GitHub API error %d, retrying in %ds", response.status_code, wait)
                time.sleep(wait)
                continue

            response.raise_for_status()

        raise RuntimeError(f"Failed to {method} {url} after {retries} attempts")

    def _check_rate_limit(self, response: requests.Response) -> None:
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining) < 10:
            logger.warning("GitHub API rate limit nearly exhausted: %s remaining", remaining)

    def _paginate(self, path: str, params: dict[str, Any] | None = None) -> list[Any]:
        """Fetch all pages of a paginated endpoint."""
        results: list[Any] = []
        page = 1
        per_page = 100
        base_params: dict[str, Any] = {**(params or {}), "per_page": per_page}

        while True:
            base_params["page"] = page
            data = self._request("GET", path, params=base_params)
            if not isinstance(data, list):
                break
            results.extend(data)
            if len(data) < per_page:
                break
            page += 1

        return results

    def _search_issues(self, query: str) -> list[dict[str, Any]]:
        """Use GitHub search API for issues/PRs."""
        results: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        while True:
            data = self._request(
                "GET",
                "/search/issues",
                params={"q": query, "per_page": per_page, "page": page},
            )
            items: list[dict[str, Any]] = data.get("items", [])
            results.extend(items)
            total: int = data.get("total_count", 0)
            if len(results) >= total or len(items) < per_page:
                break
            page += 1

        return results

    # --- Repo discovery ---

    def get_org_repos(self, org: str) -> list[str]:
        """Return list of 'org/repo' for all non-archived repos in an org."""
        repos = self._paginate(f"/orgs/{org}/repos", params={"type": "all"})
        return [
            r["full_name"] for r in repos if isinstance(r, dict) and not r.get("archived", False)
        ]

    def get_user_repos(self, user: str) -> list[str]:
        """Return list of 'owner/repo' for all non-archived repos owned by user."""
        repos = self._paginate(f"/users/{user}/repos", params={"type": "owner"})
        return [
            r["full_name"] for r in repos if isinstance(r, dict) and not r.get("archived", False)
        ]

    # --- Pull Requests ---

    def get_repo_prs(
        self,
        owner: str,
        repo: str,
        date_str: str,
    ) -> list[PullRequest]:
        """Fetch PRs created or updated on date_str, plus open PRs awaiting review."""
        prs: dict[int, PullRequest] = {}

        # updated:{date} covers PRs created, merged, or otherwise updated on that day
        updated_items = self._search_issues(f"type:pr repo:{owner}/{repo} updated:{date_str}")
        for item in updated_items:
            pr = self._parse_pr(item, f"{owner}/{repo}")
            prs[pr.number] = pr

        # Open PRs awaiting review — use REST endpoint (search doesn't support review-requested:*)
        open_prs = self._get_open_prs(owner, repo)
        for pr in open_prs:
            if pr.requested_reviewers and pr.number not in prs:
                prs[pr.number] = pr

        return list(prs.values())

    def _get_open_prs(self, owner: str, repo: str) -> list[PullRequest]:
        """Fetch all open PRs via REST API (includes requested_reviewers)."""
        items = self._paginate(f"/repos/{owner}/{repo}/pulls", params={"state": "open"})
        result: list[PullRequest] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            requested_reviewers = [
                r["login"]
                for r in item.get("requested_reviewers", [])
                if isinstance(r, dict) and r.get("login")
            ]
            merged_at = _parse_datetime(item.get("merged_at"))
            result.append(
                PullRequest(
                    number=item["number"],
                    title=item.get("title", ""),
                    url=item.get("html_url", ""),
                    state="merged" if merged_at else item.get("state", "open"),
                    author=item.get("user", {}).get("login", "unknown"),
                    repo=f"{owner}/{repo}",
                    created_at=_require_datetime(item.get("created_at")),
                    updated_at=_require_datetime(item.get("updated_at")),
                    merged_at=merged_at,
                    requested_reviewers=requested_reviewers,
                )
            )
        return result

    def _parse_pr(self, item: dict[str, Any], repo: str) -> PullRequest:
        pull_request_data: dict[str, Any] = item.get("pull_request", {})
        merged_at = _parse_datetime(pull_request_data.get("merged_at"))

        state = item.get("state", "open")
        if merged_at is not None:
            state = "merged"

        requested_reviewers: list[str] = []
        # Search API items may include requested_reviewers
        for reviewer in item.get("requested_reviewers", []):
            if isinstance(reviewer, dict):
                login = reviewer.get("login", "")
                if login:
                    requested_reviewers.append(login)

        return PullRequest(
            number=item["number"],
            title=item.get("title", ""),
            url=item.get("html_url", ""),
            state=state,
            author=item.get("user", {}).get("login", "unknown"),
            repo=repo,
            created_at=_require_datetime(item.get("created_at")),
            updated_at=_require_datetime(item.get("updated_at")),
            merged_at=merged_at,
            requested_reviewers=requested_reviewers,
        )

    def get_pr_details(self, owner: str, repo: str, pr_number: int) -> PullRequest | None:
        """Fetch full PR details including requested reviewers."""
        try:
            data = self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
        except requests.HTTPError:
            return None

        merged_at = _parse_datetime(data.get("merged_at"))
        state = data.get("state", "open")
        if merged_at is not None:
            state = "merged"

        requested_reviewers = [
            r["login"]
            for r in data.get("requested_reviewers", [])
            if isinstance(r, dict) and r.get("login")
        ]

        return PullRequest(
            number=data["number"],
            title=data.get("title", ""),
            url=data.get("html_url", ""),
            state=state,
            author=data.get("user", {}).get("login", "unknown"),
            repo=f"{owner}/{repo}",
            created_at=_require_datetime(data.get("created_at")),
            updated_at=_require_datetime(data.get("updated_at")),
            merged_at=merged_at,
            requested_reviewers=requested_reviewers,
        )

    # --- Issues ---

    def get_repo_issues(self, owner: str, repo: str, date_str: str) -> list[Issue]:
        """Fetch issues closed on date_str."""
        items = self._search_issues(f"type:issue repo:{owner}/{repo} is:closed closed:{date_str}")
        return [self._parse_issue(item, f"{owner}/{repo}") for item in items]

    def _parse_issue(self, item: dict[str, Any], repo: str) -> Issue:
        return Issue(
            number=item["number"],
            title=item.get("title", ""),
            url=item.get("html_url", ""),
            state=item.get("state", "open"),
            author=item.get("user", {}).get("login", "unknown"),
            repo=repo,
            closed_at=_parse_datetime(item.get("closed_at")),
        )

    # --- Commits ---

    def get_repo_commits(self, owner: str, repo: str, since: str, until: str) -> list[Commit]:
        """Fetch commits on the default branch between since and until."""
        try:
            items = self._paginate(
                f"/repos/{owner}/{repo}/commits",
                params={"since": since, "until": until},
            )
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 409:
                return []
            raise
        return [self._parse_commit(item, f"{owner}/{repo}") for item in items]

    def get_pr_commits(
        self, owner: str, repo: str, pr_number: int, since: str, until: str
    ) -> list[Commit]:
        """Fetch commits for a specific PR that fall within since..until."""
        try:
            items = self._paginate(f"/repos/{owner}/{repo}/pulls/{pr_number}/commits")
        except requests.HTTPError:
            return []

        result: list[Commit] = []
        for item in items:
            commit_data: dict[str, Any] = item.get("commit", {})
            author_date = commit_data.get("author", {}).get("date", "")
            if since <= author_date < until:
                result.append(self._parse_commit(item, f"{owner}/{repo}"))
        return result

    def _parse_commit(self, item: dict[str, Any], repo: str) -> Commit:
        commit_data: dict[str, Any] = item.get("commit", {})
        author_data: dict[str, Any] = commit_data.get("author", {})
        github_author: dict[str, Any] | None = item.get("author")

        # Prefer GitHub login; fall back to git author name
        author_login = (github_author.get("login", "") if github_author else "") or author_data.get(
            "name", "unknown"
        )

        return Commit(
            sha=item.get("sha", ""),
            message=commit_data.get("message", ""),
            author=author_login,
            url=item.get("html_url", ""),
            repo=repo,
            committed_at=_require_datetime(author_data.get("date")),
        )

    def get_open_prs_with_reviewers(self, owner: str, repo: str) -> list[PullRequest]:
        """Fetch open PRs that have requested reviewers."""
        items = self._search_issues(f"type:pr repo:{owner}/{repo} is:open review-requested:*")
        prs: list[PullRequest] = []
        for item in items:
            pr = self._parse_pr(item, f"{owner}/{repo}")
            # Enrich with full PR details for requested_reviewers
            detailed = self.get_pr_details(owner, repo, pr.number)
            if detailed is not None:
                prs.append(detailed)
            else:
                prs.append(pr)
        return prs
