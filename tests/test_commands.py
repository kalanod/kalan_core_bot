"""Command handling tests."""

import asyncio
from types import SimpleNamespace

from app.bot.handlers.commands import KALAN_COMMAND_RESPONSE, handle_kalan_command
from app.bot.handlers.text import _is_plain_text


class AnswerRecorder:
    """Minimal message double that records command responses."""

    def __init__(self) -> None:
        self.answers: list[str] = []

    async def answer(self, text: str) -> None:
        self.answers.append(text)


def test_kalan_command_replies_with_canned_message() -> None:
    async def check_reply() -> None:
        message = AnswerRecorder()

        await handle_kalan_command(message)  # type: ignore[arg-type]

        assert message.answers == [KALAN_COMMAND_RESPONSE]

    asyncio.run(check_reply())


def test_bot_commands_are_not_plain_text_for_broadcasts() -> None:
    assert not _is_plain_text(SimpleNamespace(text="/kalan"))  # type: ignore[arg-type]
    assert not _is_plain_text(SimpleNamespace(text="/kalan please"))  # type: ignore[arg-type]
    assert _is_plain_text(SimpleNamespace(text="обычный текст"))  # type: ignore[arg-type]
