"""Tests for configuration settings."""

import os
from unittest.mock import patch

from src.config.settings import NotifyProvider, Settings, TargetType


class TestSettings:
    def test_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            s = Settings()
        assert s.gh_token == ""
        assert s.notify_provider == ""
        assert s.github_target_type == "user_all"

    def test_from_env(self) -> None:
        env = {
            "GH_TOKEN": "ghp_abc123",
            "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/abc",
            "GITHUB_TARGET_TYPE": "org_all",
            "GITHUB_TARGET_ORG": "COFFISO",
            "NOTIFY_PROVIDER": "discord",
        }
        with patch.dict(os.environ, env, clear=True):
            s = Settings()
        assert s.gh_token == "ghp_abc123"
        assert s.discord_webhook_url == "https://discord.com/api/webhooks/123/abc"
        assert s.github_target_org == "COFFISO"
        assert s.get_target_type() == TargetType.ORG_ALL
        assert s.get_notify_provider() == NotifyProvider.DISCORD

    def test_get_target_repos(self) -> None:
        with patch.dict(
            os.environ,
            {"GITHUB_TARGET_REPOS": "COFFISO/kouchare-tv, COFFISO/ai-sensei"},
            clear=True,
        ):
            s = Settings()
        assert s.get_target_repos() == ["COFFISO/kouchare-tv", "COFFISO/ai-sensei"]

    def test_get_target_repos_empty(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            s = Settings()
        assert s.get_target_repos() == []

    def test_validate_missing_gh_token(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            s = Settings()
        errors = s.validate()
        assert any("GH_TOKEN" in e for e in errors)

    def test_validate_org_all_missing_org(self) -> None:
        with patch.dict(
            os.environ,
            {"GH_TOKEN": "token", "GITHUB_TARGET_TYPE": "org_all"},
            clear=True,
        ):
            s = Settings()
        errors = s.validate()
        assert any("GITHUB_TARGET_ORG" in e for e in errors)

    def test_validate_discord_missing_url(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GH_TOKEN": "token",
                "GITHUB_TARGET_TYPE": "user_all",
                "GITHUB_TARGET_USER": "Ruu5LP",
                "NOTIFY_PROVIDER": "discord",
            },
            clear=True,
        ):
            s = Settings()
        errors = s.validate()
        assert any("DISCORD_WEBHOOK_URL" in e for e in errors)

    def test_validate_valid(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GH_TOKEN": "token",
                "GITHUB_TARGET_TYPE": "user_all",
                "GITHUB_TARGET_USER": "Ruu5LP",
            },
            clear=True,
        ):
            s = Settings()
        errors = s.validate()
        assert errors == []

    def test_invalid_target_type_fallback(self) -> None:
        with patch.dict(os.environ, {"GITHUB_TARGET_TYPE": "invalid_type"}, clear=True):
            s = Settings()
        assert s.get_target_type() == TargetType.USER_ALL

    def test_invalid_notify_provider_returns_none(self) -> None:
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "telegram"}, clear=True):
            s = Settings()
        assert s.get_notify_provider() is None
