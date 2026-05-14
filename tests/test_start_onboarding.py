"""Start onboarding flow helpers tests."""

import asyncio
from datetime import date

from app.bot.handlers.start import (
    RESTRICTED_IMAGE_PATH,
    START_IMAGE_PATH,
    START_MESSAGE,
    WELCOME_MESSAGE,
    build_days_left_message,
    build_start_screen,
)
from app.bot.keyboards.start import ACCEPT_CLUB_VALUE_CALLBACK_DATA, build_start_accept_keyboard
from app.bot.services import UserStore
from app.bot.utils.access import is_username_allowed, parse_allow_list


def test_start_accept_keyboard_contains_single_ashente_button() -> None:
    keyboard = build_start_accept_keyboard()

    assert len(keyboard.inline_keyboard) == 1
    assert len(keyboard.inline_keyboard[0]) == 1
    button = keyboard.inline_keyboard[0][0]
    assert button.text == "ашенте!"
    assert button.callback_data == ACCEPT_CLUB_VALUE_CALLBACK_DATA


def test_start_message_and_image_asset_are_available() -> None:
    assert "Добро пожаловать в летнюю коллекцию калан core" in START_MESSAGE
    assert "Торжественно обещаю, я проведу это лето ярко!" in START_MESSAGE
    assert WELCOME_MESSAGE == "добро пожаловать в клуб"
    assert START_IMAGE_PATH.as_posix().endswith("app/static/images/init.png")
    assert RESTRICTED_IMAGE_PATH.as_posix().endswith("app/static/images/restricted.png")


def test_allowed_start_screen_contains_standard_photo_text_and_button() -> None:
    start_screen = build_start_screen("@Allowed_User", {"allowed_user"})

    assert start_screen.image_path == START_IMAGE_PATH
    assert start_screen.caption == START_MESSAGE
    assert start_screen.reply_markup is not None


def test_restricted_start_screen_contains_only_restricted_photo() -> None:
    start_screen = build_start_screen("other_user", {"allowed_user"})

    assert start_screen.image_path == RESTRICTED_IMAGE_PATH
    assert start_screen.caption is None
    assert start_screen.reply_markup is None


def test_allow_list_parses_and_matches_normalized_usernames() -> None:
    allow_list = parse_allow_list(["@Alice", " bob ", "CHARLIE", "delta"])

    assert allow_list == {"alice", "bob", "charlie", "delta"}
    assert is_username_allowed("alice", allow_list)
    assert is_username_allowed("@BOB", allow_list)
    assert not is_username_allowed(None, allow_list)
    assert not is_username_allowed("eve", allow_list)


def test_days_left_message_counts_until_project_end() -> None:
    assert build_days_left_message(date(2026, 5, 14)) == "до конца 110 дней"
    assert build_days_left_message(date(2026, 9, 2)) == "до конца 0 дней"


def test_user_store_has_user_only_after_add() -> None:
    async def check_user_membership() -> None:
        user_store = UserStore()

        assert not await user_store.has_user(123)

        await user_store.add_user(123)

        assert await user_store.has_user(123)

    asyncio.run(check_user_membership())


def test_user_store_pops_remembered_start_messages() -> None:
    async def check_start_messages() -> None:
        user_store = UserStore()

        await user_store.remember_start_message(telegram_id=123, chat_id=456, message_id=1)
        await user_store.remember_start_message(telegram_id=123, chat_id=456, message_id=2)

        assert await user_store.pop_start_messages(123) == [(456, 1), (456, 2)]
        assert await user_store.pop_start_messages(123) == []

    asyncio.run(check_start_messages())
