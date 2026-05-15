"""Text reply threading helpers tests."""

import asyncio

from app.bot.handlers.text import resolve_recipient_reply_message_id, resolve_replied_incoming_id
from app.bot.services import UserStore


class FakeTextMessageService:
    """Minimal async double for persistent reply lookup tests."""

    def __init__(self) -> None:
        self.replied_calls: list[tuple[int, int]] = []
        self.recipient_calls: list[tuple[int, int]] = []

    async def find_replied_incoming_id(
        self,
        *,
        telegram_chat_id: int,
        telegram_message_id: int,
    ) -> int | None:
        self.replied_calls.append((telegram_chat_id, telegram_message_id))
        return 42

    async def find_recipient_reply_message_id(
        self,
        *,
        incoming_message_db_id: int,
        recipient_telegram_id: int,
    ) -> int | None:
        self.recipient_calls.append((incoming_message_db_id, recipient_telegram_id))
        return 777


def test_replied_incoming_resolution_falls_back_to_database_after_cache_miss() -> None:
    async def check_resolution() -> None:
        user_store = UserStore()
        text_service = FakeTextMessageService()

        resolved_id = await resolve_replied_incoming_id(
            text_service=text_service,  # type: ignore[arg-type]
            user_store=user_store,
            chat_id=100,
            replied_message_id=55,
        )

        assert resolved_id == 42
        assert text_service.replied_calls == [(100, 55)]

    asyncio.run(check_resolution())


def test_replied_incoming_resolution_prefers_runtime_cache() -> None:
    async def check_resolution() -> None:
        user_store = UserStore()
        text_service = FakeTextMessageService()
        await user_store.remember_sent_message(
            incoming_message_db_id=10,
            recipient_telegram_id=200,
            chat_id=100,
            bot_message_id=55,
        )

        resolved_id = await resolve_replied_incoming_id(
            text_service=text_service,  # type: ignore[arg-type]
            user_store=user_store,
            chat_id=100,
            replied_message_id=55,
        )

        assert resolved_id == 10
        assert text_service.replied_calls == []

    asyncio.run(check_resolution())


def test_recipient_reply_target_falls_back_to_database_after_cache_miss() -> None:
    async def check_resolution() -> None:
        user_store = UserStore()
        text_service = FakeTextMessageService()

        message_id = await resolve_recipient_reply_message_id(
            text_service=text_service,  # type: ignore[arg-type]
            user_store=user_store,
            incoming_message_db_id=42,
            recipient_telegram_id=200,
        )

        assert message_id == 777
        assert text_service.recipient_calls == [(42, 200)]

    asyncio.run(check_resolution())


def test_recipient_reply_target_prefers_runtime_cache() -> None:
    async def check_resolution() -> None:
        user_store = UserStore()
        text_service = FakeTextMessageService()
        await user_store.remember_sent_message(
            incoming_message_db_id=42,
            recipient_telegram_id=200,
            chat_id=100,
            bot_message_id=888,
        )

        message_id = await resolve_recipient_reply_message_id(
            text_service=text_service,  # type: ignore[arg-type]
            user_store=user_store,
            incoming_message_db_id=42,
            recipient_telegram_id=200,
        )

        assert message_id == 888
        assert text_service.recipient_calls == []

    asyncio.run(check_resolution())
