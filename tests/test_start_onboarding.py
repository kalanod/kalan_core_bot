"""Start onboarding flow helpers tests."""

import asyncio

from app.bot.handlers.start import START_IMAGE_PATH, START_MESSAGE, WELCOME_MESSAGE
from app.bot.keyboards.start import ACCEPT_CLUB_VALUE_CALLBACK_DATA, build_start_accept_keyboard
from app.bot.services import UserStore


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


def test_user_store_has_user_only_after_add() -> None:
    async def check_user_membership() -> None:
        user_store = UserStore()

        assert not await user_store.has_user(123)

        await user_store.add_user(123)

        assert await user_store.has_user(123)

    asyncio.run(check_user_membership())
