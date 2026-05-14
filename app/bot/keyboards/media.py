"""Inline keyboards for media broadcasts."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

OTTER_ACTION = "otter"
STONE_FACE_ACTION = "stone_face"
UNDO_REACTION_ACTION = "undo"
DELETE_MEDIA_ACTION = "delete"


def build_media_reaction_keyboard(
    *,
    otter_callback_data: str,
    stone_face_callback_data: str,
) -> InlineKeyboardMarkup:
    """Build the two-button media reaction keyboard required for every recipient."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🦦", callback_data=otter_callback_data),
                InlineKeyboardButton(text="🗿", callback_data=stone_face_callback_data),
            ]
        ]
    )


def build_media_score_keyboard(
    *,
    approves: int,
    declines: int,
    undo_callback_data: str,
) -> InlineKeyboardMarkup:
    """Build one toggle button with a 20-symbol otter/stone-face score bar."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=build_media_score_text(approves=approves, declines=declines),
                    callback_data=undo_callback_data,
                )
            ]
        ]
    )


def build_media_score_text(*, approves: int, declines: int) -> str:
    """Return a 20-symbol score bar based on the approve share."""
    total = approves + declines
    otter_count = 0 if total <= 0 else round((approves / total) * 20)
    otter_count = min(20, max(0, otter_count))
    return "🦦" * otter_count + "🗿" * (20 - otter_count)


def build_media_delete_score_keyboard(
    *, approves: int, declines: int, delete_callback_data: str
) -> InlineKeyboardMarkup:
    """Build sender-facing score button that deletes the media package when pressed."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=build_media_score_text(approves=approves, declines=declines),
                    callback_data=delete_callback_data,
                )
            ]
        ]
    )
