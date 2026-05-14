"""Helpers for extracting reusable Telegram media identifiers."""

from dataclasses import dataclass

from aiogram.types import Message


@dataclass(frozen=True)
class ExtractedMedia:
    """Reusable Telegram file id plus the supported media kind."""

    file_id: str
    media_type: str


def extract_media(message: Message) -> ExtractedMedia | None:
    """Return reusable Telegram file metadata for supported photo/video messages."""
    if message.photo:
        return ExtractedMedia(file_id=message.photo[-1].file_id, media_type="photo")
    if message.video:
        return ExtractedMedia(file_id=message.video.file_id, media_type="video")
    return None


def extract_kalan_id(message: Message) -> str | None:
    """Return the reusable Telegram file id for supported photo/video messages."""
    media = extract_media(message)
    if media is None:
        return None
    return media.file_id
