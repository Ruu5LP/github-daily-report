"""Tests for notification providers."""

from unittest.mock import MagicMock, patch

import pytest

from src.config.settings import Settings
from src.notification.discord import DISCORD_MAX_CHARS, DiscordNotifier
from src.notification.factory import NotifierFactory, StdoutNotifier
from src.notification.lark import LarkNotifier
from src.notification.line import LineBotNotifier


class TestDiscordNotifier:
    def test_requires_webhook_url(self) -> None:
        with pytest.raises(ValueError, match="DISCORD_WEBHOOK_URL"):
            DiscordNotifier("")

    def test_send_short_message(self) -> None:
        notifier = DiscordNotifier("https://discord.com/webhook")
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=204)
            mock_post.return_value.raise_for_status = MagicMock()
            notifier.send("Hello, world!")
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["content"] == "Hello, world!"

    def test_send_long_message_splits(self) -> None:
        notifier = DiscordNotifier("https://discord.com/webhook")
        # Create a message just over 2000 chars
        line = "x" * 100 + "\n"
        message = line * 25  # 2525 chars
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=204)
            mock_post.return_value.raise_for_status = MagicMock()
            notifier.send(message)
        assert mock_post.call_count >= 2

    def test_split_respects_newlines(self) -> None:
        notifier = DiscordNotifier("https://discord.com/webhook")
        # Build a message just over limit
        message = ("a" * 100 + "\n") * 21  # 21 * 101 = 2121 chars
        chunks = notifier._split_message(message)
        assert all(len(c) <= DISCORD_MAX_CHARS for c in chunks)
        assert "".join(chunks) == message

    def test_split_single_line_over_limit(self) -> None:
        notifier = DiscordNotifier("https://discord.com/webhook")
        long_line = "x" * 5000
        chunks = notifier._split_message(long_line)
        assert all(len(c) <= DISCORD_MAX_CHARS for c in chunks)
        assert "".join(chunks) == long_line

    def test_short_message_not_split(self) -> None:
        notifier = DiscordNotifier("https://discord.com/webhook")
        chunks = notifier._split_message("short")
        assert chunks == ["short"]


class TestLarkNotifier:
    def test_requires_webhook_url(self) -> None:
        with pytest.raises(ValueError, match="LARK_WEBHOOK_URL"):
            LarkNotifier("")

    def test_send_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        notifier = LarkNotifier("https://lark.example.com/webhook")
        with caplog.at_level(logging.WARNING):
            notifier.send("hello")
        assert any("stub" in r.message.lower() for r in caplog.records)


class TestLineBotNotifier:
    def test_requires_token(self) -> None:
        with pytest.raises(ValueError, match="LINE_CHANNEL_ACCESS_TOKEN"):
            LineBotNotifier("", "user123")

    def test_requires_line_to(self) -> None:
        with pytest.raises(ValueError, match="LINE_TO"):
            LineBotNotifier("token123", "")

    def test_send_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        notifier = LineBotNotifier("token123", "user123")
        with caplog.at_level(logging.WARNING):
            notifier.send("hello")
        assert any("stub" in r.message.lower() for r in caplog.records)


class TestNotifierFactory:
    def _make_settings(self, **kwargs: str) -> Settings:
        import os

        # Build a real Settings with overrides
        env = {
            "GH_TOKEN": "token",
            "GITHUB_TARGET_TYPE": "user_all",
            "GITHUB_TARGET_USER": "testuser",
            **kwargs,
        }
        with patch.dict(os.environ, env, clear=True):
            return Settings()

    def test_no_provider_returns_stdout(self) -> None:
        settings = self._make_settings()
        notifier = NotifierFactory.create(settings)
        assert isinstance(notifier, StdoutNotifier)

    def test_discord_provider(self) -> None:
        settings = self._make_settings(
            NOTIFY_PROVIDER="discord",
            DISCORD_WEBHOOK_URL="https://discord.com/webhook",
        )
        notifier = NotifierFactory.create(settings)
        assert isinstance(notifier, DiscordNotifier)

    def test_discord_missing_url_fallback(self) -> None:
        settings = self._make_settings(NOTIFY_PROVIDER="discord")
        notifier = NotifierFactory.create(settings)
        assert isinstance(notifier, StdoutNotifier)

    def test_lark_provider(self) -> None:
        settings = self._make_settings(
            NOTIFY_PROVIDER="lark",
            LARK_WEBHOOK_URL="https://lark.example.com/webhook",
        )
        notifier = NotifierFactory.create(settings)
        assert isinstance(notifier, LarkNotifier)

    def test_line_provider(self) -> None:
        settings = self._make_settings(
            NOTIFY_PROVIDER="line",
            LINE_CHANNEL_ACCESS_TOKEN="token123",
            LINE_TO="user123",
        )
        notifier = NotifierFactory.create(settings)
        assert isinstance(notifier, LineBotNotifier)

    def test_stdout_send_prints(self, capsys: pytest.CaptureFixture[str]) -> None:
        notifier = StdoutNotifier()
        notifier.send("test message")
        captured = capsys.readouterr()
        assert "test message" in captured.out
