"""Inline keyboards for media broadcasts."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

OTTER_ACTION = "otter"
STONE_FACE_ACTION = "stone_face"


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
