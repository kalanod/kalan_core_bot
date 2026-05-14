"""Business operations for media fan-out broadcasts and reaction callbacks."""

import secrets
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.database.models import MediaDelivery, MediaMessage, MediaReactionButton
from app.bot.keyboards.media import OTTER_ACTION, STONE_FACE_ACTION
from app.bot.repositories import KalanRepository, MediaMessageRepository, UserRepository


@dataclass(frozen=True)
class IncomingMediaRegistrationResult:
    """Result returned after incoming media metadata has been persisted."""

    message: MediaMessage
    sender_created: bool
    kalan_created: bool


@dataclass(frozen=True)
class PreparedMediaDelivery:
    """A persisted recipient delivery plus its per-user button callback payloads."""

    delivery: MediaDelivery
    otter_callback_data: str
    stone_face_callback_data: str


class MediaMessageService:
    """Application service for media persistence, fan-out state, and callbacks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._kalans = KalanRepository(session)
        self._media_messages = MediaMessageRepository(session)

    async def register_incoming(
        self,
        *,
        sender_telegram_id: int,
        telegram_chat_id: int,
        telegram_message_id: int,
        telegram_file_id: str,
        media_type: str,
        caption: str | None,
        date: datetime | None,
    ) -> IncomingMediaRegistrationResult:
        """Persist incoming media, sender, reusable Telegram file id, and caption metadata."""
        user = await self._users.get_by_telegram_id(sender_telegram_id)
        sender_created = user is None
        if user is None:
            user = await self._users.get_or_create(sender_telegram_id)

        existing_kalan = await self._kalans.get_by_kalan_id(telegram_file_id)
        kalan_created = existing_kalan is None
        kalan = existing_kalan or await self._kalans.create(
            kalan_id=telegram_file_id,
            owner_id=user.id,
        )
        media_message = await self._media_messages.create_message(
            telegram_message_id=telegram_message_id,
            telegram_chat_id=telegram_chat_id,
            sender_telegram_id=sender_telegram_id,
            direction="incoming",
            media_type=media_type,
            caption=caption,
            date=date,
            sender_id=user.id,
            kalan_id=kalan.id,
        )
        await self._session.commit()
        return IncomingMediaRegistrationResult(
            message=media_message,
            sender_created=sender_created,
            kalan_created=kalan_created,
        )

    async def prepare_delivery(
        self,
        *,
        incoming_media_message_id: int,
        recipient_telegram_id: int,
    ) -> PreparedMediaDelivery:
        """Persist a delivery package and both recipient-specific buttons before sending."""
        delivery = await self._media_messages.create_delivery(
            incoming_media_message_id=incoming_media_message_id,
            recipient_telegram_id=recipient_telegram_id,
        )
        otter_callback_data = self._build_callback_data(delivery.id, OTTER_ACTION)
        stone_face_callback_data = self._build_callback_data(delivery.id, STONE_FACE_ACTION)
        await self._media_messages.create_reaction_button(
            delivery_id=delivery.id,
            recipient_telegram_id=recipient_telegram_id,
            action=OTTER_ACTION,
            callback_data=otter_callback_data,
        )
        await self._media_messages.create_reaction_button(
            delivery_id=delivery.id,
            recipient_telegram_id=recipient_telegram_id,
            action=STONE_FACE_ACTION,
            callback_data=stone_face_callback_data,
        )
        await self._session.commit()
        return PreparedMediaDelivery(
            delivery=delivery,
            otter_callback_data=otter_callback_data,
            stone_face_callback_data=stone_face_callback_data,
        )

    async def register_outgoing(
        self,
        *,
        sender_telegram_id: int,
        recipient_telegram_id: int,
        telegram_chat_id: int,
        telegram_message_id: int,
        media_type: str,
        caption: str | None,
        date: datetime | None,
        kalan_id: int,
        mirrored_from_media_message_id: int,
        delivery_id: int,
    ) -> MediaMessage:
        """Persist sent media metadata and connect it to the prepared delivery package."""
        media_message = await self._media_messages.create_message(
            telegram_message_id=telegram_message_id,
            telegram_chat_id=telegram_chat_id,
            sender_telegram_id=sender_telegram_id,
            recipient_telegram_id=recipient_telegram_id,
            direction="outgoing",
            media_type=media_type,
            caption=caption,
            date=date,
            kalan_id=kalan_id,
            mirrored_from_media_message_id=mirrored_from_media_message_id,
        )
        await self._media_messages.mark_delivery_sent(
            delivery_id=delivery_id,
            outgoing_media_message_id=media_message.id,
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
        )
        await self._session.commit()
        return media_message

    async def register_delivery_failure(self, *, delivery_id: int, error: str) -> None:
        """Persist that a prepared media package could not be sent."""
        await self._media_messages.mark_delivery_failed(delivery_id=delivery_id, error=error)
        await self._session.commit()

    async def register_reaction_click(
        self, *, callback_data: str, user_telegram_id: int
    ) -> MediaReactionButton | None:
        """Load and mark a stored reaction button if the callback belongs to this user."""
        button = await self._media_messages.get_reaction_button_by_callback_data(callback_data)
        if button is None or button.recipient_telegram_id != user_telegram_id:
            await self._session.commit()
            return None

        button = await self._media_messages.mark_reaction_button_clicked(
            callback_data=callback_data,
        )
        await self._session.commit()
        return button

    @staticmethod
    def _build_callback_data(delivery_id: int, action: str) -> str:
        """Build compact callback data that fits Telegram's 64-byte callback_data limit."""
        return f"mr:{delivery_id}:{action}:{secrets.token_urlsafe(6)}"
