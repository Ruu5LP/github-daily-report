"""Discord webhook notifier."""

from __future__ import annotations

import requests

from src.notification.base import Notifier
from src.utils.logger import logger

DISCORD_MAX_CHARS = 2000


class DiscordNotifier(Notifier):
    def __init__(self, webhook_url: str) -> None:
        if not webhook_url:
            raise ValueError("DISCORD_WEBHOOK_URL must not be empty")
        self._webhook_url = webhook_url

    def send(self, message: str) -> None:
        chunks = self._split_message(message)
        logger.info("Sending %d chunk(s) to Discord", len(chunks))
        for i, chunk in enumerate(chunks, 1):
            self._post(chunk)
            logger.debug("Sent chunk %d/%d", i, len(chunks))

    def _post(self, content: str) -> None:
        response = requests.post(
            self._webhook_url,
            json={"content": content},
            timeout=30,
        )
        response.raise_for_status()

    def _split_message(self, message: str) -> list[str]:
        """Split message into chunks of at most DISCORD_MAX_CHARS, breaking at newlines."""
        if len(message) <= DISCORD_MAX_CHARS:
            return [message]

        chunks: list[str] = []
        current_lines: list[str] = []
        current_len = 0

        for line in message.splitlines(keepends=True):
            line_len = len(line)

            # A single line longer than max — force split it
            if line_len > DISCORD_MAX_CHARS:
                if current_lines:
                    chunks.append("".join(current_lines))
                    current_lines = []
                    current_len = 0
                for i in range(0, line_len, DISCORD_MAX_CHARS):
                    chunks.append(line[i : i + DISCORD_MAX_CHARS])
                continue

            if current_len + line_len > DISCORD_MAX_CHARS:
                chunks.append("".join(current_lines))
                current_lines = []
                current_len = 0

            current_lines.append(line)
            current_len += line_len

        if current_lines:
            chunks.append("".join(current_lines))

        return chunks
