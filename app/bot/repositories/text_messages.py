"""Persistence operations for Telegram text message metadata."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.database.models import TextMessage


class TextMessageRepository:
    """Small data access object for text message records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        telegram_message_id: int,
        telegram_chat_id: int,
        sender_telegram_id: int,
        text: str,
        recipient_telegram_id: int | None = None,
        direction: str,
        date: datetime | None,
        sender_id: int | None = None,
        reply_to_text_message_id: int | None = None,
        mirrored_from_text_message_id: int | None = None,
    ) -> TextMessage:
        """Persist metadata for one Telegram text message."""
        text_message = TextMessage(
            telegram_message_id=telegram_message_id,
            telegram_chat_id=telegram_chat_id,
            sender_telegram_id=sender_telegram_id,
            recipient_telegram_id=recipient_telegram_id,
            text=text,
            direction=direction,
            date=date,
            sender_id=sender_id,
            reply_to_text_message_id=reply_to_text_message_id,
            mirrored_from_text_message_id=mirrored_from_text_message_id,
        )
        self._session.add(text_message)
        await self._session.flush()
        return text_message

    async def get_by_chat_message(
        self,
        *,
        telegram_chat_id: int,
        telegram_message_id: int,
    ) -> TextMessage | None:
        """Return a message stored for a Telegram chat/message pair, if any."""
        result = await self._session.execute(
            select(TextMessage).where(
                TextMessage.telegram_chat_id == telegram_chat_id,
                TextMessage.telegram_message_id == telegram_message_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, text_message_id: int) -> TextMessage | None:
        """Return a text message by database id, if it exists."""
        result = await self._session.execute(
            select(TextMessage).where(TextMessage.id == text_message_id)
        )
        return result.scalar_one_or_none()

    async def get_outgoing_mirror_for_recipient(
        self,
        *,
        incoming_text_message_id: int,
        recipient_telegram_id: int,
    ) -> TextMessage | None:
        """Return the recipient-local bot copy of an incoming message, if it exists."""
        result = await self._session.execute(
            select(TextMessage)
            .where(
                TextMessage.mirrored_from_text_message_id == incoming_text_message_id,
                TextMessage.recipient_telegram_id == recipient_telegram_id,
                TextMessage.direction == "outgoing",
            )
            .order_by(TextMessage.id.desc())
        )
        return result.scalars().first()
