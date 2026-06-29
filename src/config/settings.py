"""Configuration settings loaded from environment variables."""

import os
from dataclasses import dataclass, field
from enum import StrEnum

from dotenv import load_dotenv

load_dotenv()


class TargetType(StrEnum):
    ORG_ALL = "org_all"
    USER_ALL = "user_all"
    REPOS = "repos"


class NotifyProvider(StrEnum):
    DISCORD = "discord"
    LARK = "lark"
    LINE = "line"
    STDOUT = "stdout"


@dataclass
class Settings:
    # Secrets
    gh_token: str = field(default_factory=lambda: os.environ.get("GH_TOKEN", ""))
    discord_webhook_url: str = field(
        default_factory=lambda: os.environ.get("DISCORD_WEBHOOK_URL", "")
    )
    lark_webhook_url: str = field(default_factory=lambda: os.environ.get("LARK_WEBHOOK_URL", ""))
    line_channel_access_token: str = field(
        default_factory=lambda: os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    )

    # Variables
    github_target_type: str = field(
        default_factory=lambda: os.environ.get("GITHUB_TARGET_TYPE", "user_all")
    )
    github_target_org: str = field(default_factory=lambda: os.environ.get("GITHUB_TARGET_ORG", ""))
    github_target_user: str = field(
        default_factory=lambda: os.environ.get("GITHUB_TARGET_USER", "")
    )
    github_target_repos: str = field(
        default_factory=lambda: os.environ.get("GITHUB_TARGET_REPOS", "")
    )
    notify_provider: str = field(default_factory=lambda: os.environ.get("NOTIFY_PROVIDER", ""))
    line_to: str = field(default_factory=lambda: os.environ.get("LINE_TO", ""))

    def get_target_type(self) -> TargetType:
        try:
            return TargetType(self.github_target_type)
        except ValueError:
            return TargetType.USER_ALL

    def get_target_repos(self) -> list[str]:
        """Parse comma-separated repos into a list."""
        if not self.github_target_repos:
            return []
        return [r.strip() for r in self.github_target_repos.split(",") if r.strip()]

    def get_notify_provider(self) -> NotifyProvider | None:
        if not self.notify_provider:
            return None
        try:
            return NotifyProvider(self.notify_provider.lower())
        except ValueError:
            return None

    def validate(self) -> list[str]:
        """Return a list of validation error messages."""
        errors: list[str] = []

        if not self.gh_token:
            errors.append("GH_TOKEN is required")

        target_type = self.get_target_type()
        if target_type == TargetType.ORG_ALL and not self.github_target_org:
            errors.append("GITHUB_TARGET_ORG is required when GITHUB_TARGET_TYPE=org_all")
        if target_type == TargetType.USER_ALL and not self.github_target_user:
            errors.append("GITHUB_TARGET_USER is required when GITHUB_TARGET_TYPE=user_all")
        if target_type == TargetType.REPOS and not self.github_target_repos:
            errors.append("GITHUB_TARGET_REPOS is required when GITHUB_TARGET_TYPE=repos")

        provider = self.get_notify_provider()
        if provider == NotifyProvider.DISCORD and not self.discord_webhook_url:
            errors.append("DISCORD_WEBHOOK_URL is required when NOTIFY_PROVIDER=discord")

        return errors


def load_settings() -> Settings:
    return Settings()
