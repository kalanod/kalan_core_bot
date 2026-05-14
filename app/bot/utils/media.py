"""Helpers for extracting reusable Telegram media identifiers."""

from aiogram.types import Message


def extract_kalan_id(message: Message) -> str | None:
    """Return the reusable Telegram file id for supported photo/video messages."""
    if message.photo:
        return message.photo[-1].file_id
    if message.video:
        return message.video.file_id
    return None
