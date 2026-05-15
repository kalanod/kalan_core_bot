"""In-memory user and message relation storage for broadcast routing."""

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.bot.services.message_replies import MessageReference


@dataclass
class UserStore:
    """Runtime source of truth for known Telegram users and reply mappings."""

    _user_ids: set[int] = field(default_factory=set)
    _bot_messages_to_incoming_refs: dict[tuple[int, int], MessageReference] = field(
        default_factory=dict
    )
    _incoming_refs_to_sent_messages: dict[MessageReference, dict[int, int]] = field(
        default_factory=dict
    )
    _start_messages: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def replace_users(self, user_ids: Iterable[int]) -> None:
        """Replace known users with ids loaded from persistent storage."""
        async with self._lock:
            self._user_ids = set(user_ids)

    async def add_user(self, telegram_id: int) -> None:
        """Add a user id after the database transaction that created it succeeds."""
        async with self._lock:
            self._user_ids.add(telegram_id)

    async def has_user(self, telegram_id: int) -> bool:
        """Return whether the Telegram id belongs to an accepted club member."""
        async with self._lock:
            return telegram_id in self._user_ids

    async def other_users(self, telegram_id: int) -> list[int]:
        """Return all known users except the provided sender id."""
        async with self._lock:
            return [user_id for user_id in self._user_ids if user_id != telegram_id]

    async def remember_start_message(
        self,
        *,
        telegram_id: int,
        chat_id: int,
        message_id: int,
    ) -> None:
        """Remember a bot onboarding message so future /start commands can delete it."""
        async with self._lock:
            self._start_messages.setdefault(telegram_id, []).append((chat_id, message_id))

    async def pop_start_messages(self, telegram_id: int) -> list[tuple[int, int]]:
        """Remove and return remembered onboarding messages for a Telegram user."""
        async with self._lock:
            return self._start_messages.pop(telegram_id, [])

    async def remember_sent_broadcast_message(
        self,
        *,
        incoming_message: MessageReference,
        recipient_telegram_id: int,
        chat_id: int,
        bot_message_id: int,
    ) -> None:
        """Remember which bot message mirrors an incoming text/media message."""
        async with self._lock:
            self._bot_messages_to_incoming_refs[(chat_id, bot_message_id)] = incoming_message
            self._incoming_refs_to_sent_messages.setdefault(incoming_message, {})[
                recipient_telegram_id
            ] = bot_message_id

    async def get_replied_incoming_ref(
        self, *, chat_id: int, bot_message_id: int
    ) -> MessageReference | None:
        """Return the original incoming broadcast mirrored by a bot message, if known."""
        async with self._lock:
            return self._bot_messages_to_incoming_refs.get((chat_id, bot_message_id))

    async def get_recipient_broadcast_reply_message_id(
        self,
        *,
        incoming_message: MessageReference,
        recipient_telegram_id: int,
    ) -> int | None:
        """Return recipient-local bot message id to use as reply target, if known."""
        async with self._lock:
            return self._incoming_refs_to_sent_messages.get(incoming_message, {}).get(
                recipient_telegram_id
            )

    async def remember_sent_message(
        self,
        *,
        incoming_message_db_id: int,
        recipient_telegram_id: int,
        chat_id: int,
        bot_message_id: int,
    ) -> None:
        """Remember which bot message mirrors an incoming text message for a recipient."""
        await self.remember_sent_broadcast_message(
            incoming_message=MessageReference(kind="text", id=incoming_message_db_id),
            recipient_telegram_id=recipient_telegram_id,
            chat_id=chat_id,
            bot_message_id=bot_message_id,
        )

    async def get_replied_incoming_id(self, *, chat_id: int, bot_message_id: int) -> int | None:
        """Return the original incoming text id mirrored by a bot message, if known."""
        incoming_ref = await self.get_replied_incoming_ref(
            chat_id=chat_id,
            bot_message_id=bot_message_id,
        )
        if incoming_ref is None or incoming_ref.kind != "text":
            return None
        return incoming_ref.id

    async def get_recipient_reply_message_id(
        self,
        *,
        incoming_message_db_id: int,
        recipient_telegram_id: int,
    ) -> int | None:
        """Return recipient-local text bot message id to use as reply target, if known."""
        return await self.get_recipient_broadcast_reply_message_id(
            incoming_message=MessageReference(kind="text", id=incoming_message_db_id),
            recipient_telegram_id=recipient_telegram_id,
        )
