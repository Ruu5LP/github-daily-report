"""Lark (Feishu) webhook notifier — stub implementation."""

from __future__ import annotations

from src.notification.base import Notifier
from src.utils.logger import logger


class LarkNotifier(Notifier):
    """Stub notifier for Lark webhook.

    Full implementation pending. Currently logs a warning and does nothing.
    Set LARK_WEBHOOK_URL to enable in the future.
    """

    def __init__(self, webhook_url: str) -> None:
        if not webhook_url:
            raise ValueError("LARK_WEBHOOK_URL must not be empty")
        self._webhook_url = webhook_url

    def send(self, message: str) -> None:
        logger.warning("LarkNotifier is a stub — message not sent (length=%d)", len(message))
