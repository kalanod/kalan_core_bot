"""Unified reply threading support for text and media broadcasts."""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.repositories import MediaMessageRepository, TextMessageRepository

MessageKind = Literal["text", "media"]


@dataclass(frozen=True)
class MessageReference:
    """Database identity of an original incoming broadcast message."""

    kind: MessageKind
    id: int


class MessageReplyService:
    """Resolve Telegram reply targets across all broadcast message types.

    Recipients reply to bot-created copies whose Telegram ids are local to their chats.
    This service maps any known text/media Telegram message back to the original incoming
    broadcast, then maps that original broadcast to the recipient-local message that can
    be used as Telegram's ``reply_to_message_id``.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._text_messages = TextMessageRepository(session)
        self._media_messages = MediaMessageRepository(session)

    async def find_replied_incoming_ref(
        self,
        *,
        telegram_chat_id: int,
        telegram_message_id: int,
    ) -> MessageReference | None:
        """Resolve a replied Telegram message to an original incoming text/media reference."""
        text_message = await self._text_messages.get_by_chat_message(
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
        )
        if text_message is not None:
            return MessageReference(
                kind="text",
                id=text_message.mirrored_from_text_message_id or text_message.id,
            )

        media_message = await self._media_messages.get_by_chat_message(
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
        )
        if media_message is not None:
            return MessageReference(
                kind="media",
                id=media_message.mirrored_from_media_message_id or media_message.id,
            )

        return None

    async def find_recipient_reply_message_id(
        self,
        *,
        incoming_message: MessageReference,
        recipient_telegram_id: int,
    ) -> int | None:
        """Return a recipient-local Telegram message id for replying to a broadcast."""
        if incoming_message.kind == "text":
            incoming_text = await self._text_messages.get_by_id(incoming_message.id)
            if incoming_text is None:
                return None
            if (
                incoming_text.direction == "incoming"
                and incoming_text.sender_telegram_id == recipient_telegram_id
            ):
                return incoming_text.telegram_message_id

            outgoing_text = await self._text_messages.get_outgoing_mirror_for_recipient(
                incoming_text_message_id=incoming_message.id,
                recipient_telegram_id=recipient_telegram_id,
            )
            if outgoing_text is None:
                return None
            return outgoing_text.telegram_message_id

        incoming_media = await self._media_messages.get_by_id(incoming_message.id)
        if incoming_media is None:
            return None
        if (
            incoming_media.direction == "incoming"
            and incoming_media.sender_telegram_id == recipient_telegram_id
        ):
            return incoming_media.telegram_message_id

        outgoing_media = await self._media_messages.get_outgoing_mirror_for_recipient(
            incoming_media_message_id=incoming_message.id,
            recipient_telegram_id=recipient_telegram_id,
        )
        if outgoing_media is None:
            return None
        return outgoing_media.telegram_message_id
