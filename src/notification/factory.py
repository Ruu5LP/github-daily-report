"""NotifierFactory — creates the appropriate Notifier based on provider name."""

from __future__ import annotations

from src.config.settings import NotifyProvider, Settings
from src.notification.base import Notifier
from src.notification.discord import DiscordNotifier
from src.notification.lark import LarkNotifier
from src.notification.line import LineBotNotifier
from src.utils.logger import logger


class StdoutNotifier(Notifier):
    """Fallback notifier that prints to stdout."""

    def send(self, message: str) -> None:
        print(message)


class NotifierFactory:
    @staticmethod
    def create(settings: Settings) -> Notifier:
        """Create a Notifier based on NOTIFY_PROVIDER setting.

        Falls back to StdoutNotifier when provider is not set or credentials are missing.
        """
        provider = settings.get_notify_provider()

        if provider == NotifyProvider.DISCORD:
            if not settings.discord_webhook_url:
                logger.warning(
                    "NOTIFY_PROVIDER=discord but DISCORD_WEBHOOK_URL not set; "
                    "falling back to stdout"
                )
                return StdoutNotifier()
            return DiscordNotifier(settings.discord_webhook_url)

        if provider == NotifyProvider.LARK:
            if not settings.lark_webhook_url:
                logger.warning(
                    "NOTIFY_PROVIDER=lark but LARK_WEBHOOK_URL not set; falling back to stdout"
                )
                return StdoutNotifier()
            return LarkNotifier(settings.lark_webhook_url)

        if provider == NotifyProvider.LINE:
            if not settings.line_channel_access_token:
                logger.warning(
                    "NOTIFY_PROVIDER=line but LINE_CHANNEL_ACCESS_TOKEN not set; "
                    "falling back to stdout"
                )
                return StdoutNotifier()
            return LineBotNotifier(settings.line_channel_access_token, settings.line_to)

        if provider is not None:
            logger.warning("Unknown NOTIFY_PROVIDER=%r; falling back to stdout", provider)

        return StdoutNotifier()

    @staticmethod
    def create_stdout() -> Notifier:
        return StdoutNotifier()
