"""Inline keyboards for the onboarding flow."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

ACCEPT_CLUB_VALUE_CALLBACK_DATA = "start:accept"


def build_start_accept_keyboard() -> InlineKeyboardMarkup:
    """Build the onboarding confirmation keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="ашенте!",
                    callback_data=ACCEPT_CLUB_VALUE_CALLBACK_DATA,
                )
            ]
        ]
    )
