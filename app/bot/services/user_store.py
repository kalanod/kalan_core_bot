"""In-memory user and message relation storage for broadcast routing."""

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass
class UserStore:
    """Runtime source of truth for known Telegram users and reply mappings."""

    _user_ids: set[int] = field(default_factory=set)
    _bot_messages_to_incoming_ids: dict[tuple[int, int], int] = field(default_factory=dict)
    _incoming_ids_to_sent_messages: dict[int, dict[int, int]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def replace_users(self, user_ids: Iterable[int]) -> None:
        """Replace known users with ids loaded from persistent storage."""
        async with self._lock:
            self._user_ids = set(user_ids)

    async def add_user(self, telegram_id: int) -> None:
        """Add a user id after the database transaction that created it succeeds."""
        async with self._lock:
            self._user_ids.add(telegram_id)

    async def other_users(self, telegram_id: int) -> list[int]:
        """Return all known users except the provided sender id."""
        async with self._lock:
            return [user_id for user_id in self._user_ids if user_id != telegram_id]

    async def remember_sent_message(
        self,
        *,
        incoming_message_db_id: int,
        recipient_telegram_id: int,
        chat_id: int,
        bot_message_id: int,
    ) -> None:
        """Remember which bot message mirrors an incoming text message for a recipient."""
        async with self._lock:
            self._bot_messages_to_incoming_ids[(chat_id, bot_message_id)] = incoming_message_db_id
            self._incoming_ids_to_sent_messages.setdefault(incoming_message_db_id, {})[
                recipient_telegram_id
            ] = bot_message_id

    async def get_replied_incoming_id(self, *, chat_id: int, bot_message_id: int) -> int | None:
        """Return the original incoming message id mirrored by a bot message, if known."""
        async with self._lock:
            return self._bot_messages_to_incoming_ids.get((chat_id, bot_message_id))

    async def get_recipient_reply_message_id(
        self,
        *,
        incoming_message_db_id: int,
        recipient_telegram_id: int,
    ) -> int | None:
        """Return recipient-local bot message id to use as reply target, if known."""
        async with self._lock:
            return self._incoming_ids_to_sent_messages.get(incoming_message_db_id, {}).get(
                recipient_telegram_id
            )
