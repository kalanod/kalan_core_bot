"""Business operations related to Telegram text message broadcasts."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.database.models import TextMessage
from app.bot.repositories import TextMessageRepository, UserRepository


@dataclass(frozen=True)
class IncomingTextRegistrationResult:
    """Result returned after storing an incoming text message."""

    message: TextMessage
    sender_created: bool


class TextMessageService:
    """Application service for text message persistence flows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._text_messages = TextMessageRepository(session)
        self._users = UserRepository(session)

    async def register_incoming(
        self,
        *,
        sender_telegram_id: int,
        telegram_chat_id: int,
        telegram_message_id: int,
        text: str,
        date: datetime | None,
        reply_to_text_message_id: int | None,
    ) -> IncomingTextRegistrationResult:
        """Persist incoming user text and ensure the sender exists."""
        user = await self._users.get_by_telegram_id(sender_telegram_id)
        sender_created = user is None
        if user is None:
            user = await self._users.get_or_create(sender_telegram_id)

        text_message = await self._text_messages.create(
            telegram_message_id=telegram_message_id,
            telegram_chat_id=telegram_chat_id,
            sender_telegram_id=sender_telegram_id,
            text=text,
            direction="incoming",
            date=date,
            sender_id=user.id,
            reply_to_text_message_id=reply_to_text_message_id,
        )
        await self._session.commit()
        return IncomingTextRegistrationResult(message=text_message, sender_created=sender_created)

    async def register_outgoing(
        self,
        *,
        sender_telegram_id: int,
        recipient_telegram_id: int,
        telegram_chat_id: int,
        telegram_message_id: int,
        text: str,
        date: datetime | None,
        mirrored_from_text_message_id: int,
        reply_to_text_message_id: int | None,
    ) -> TextMessage:
        """Persist metadata for a bot message sent to a recipient."""
        text_message = await self._text_messages.create(
            telegram_message_id=telegram_message_id,
            telegram_chat_id=telegram_chat_id,
            sender_telegram_id=sender_telegram_id,
            recipient_telegram_id=recipient_telegram_id,
            text=text,
            direction="outgoing",
            date=date,
            mirrored_from_text_message_id=mirrored_from_text_message_id,
            reply_to_text_message_id=reply_to_text_message_id,
        )
        await self._session.commit()
        return text_message
