"""LINE Bot notifier — stub implementation."""

from __future__ import annotations

from src.notification.base import Notifier
from src.utils.logger import logger


class LineBotNotifier(Notifier):
    """Stub notifier for LINE Bot.

    Full implementation pending. Currently logs a warning and does nothing.
    Set LINE_CHANNEL_ACCESS_TOKEN and LINE_TO to enable in the future.
    """

    def __init__(self, channel_access_token: str, line_to: str) -> None:
        if not channel_access_token:
            raise ValueError("LINE_CHANNEL_ACCESS_TOKEN must not be empty")
        if not line_to:
            raise ValueError("LINE_TO must not be empty")
        self._token = channel_access_token
        self._to = line_to

    def send(self, message: str) -> None:
        logger.warning(
            "LineBotNotifier is a stub — message not sent to %s (length=%d)",
            self._to,
            len(message),
        )
