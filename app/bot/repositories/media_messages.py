"""Persistence operations for Telegram media broadcast metadata."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.database.models import MediaDelivery, MediaMessage, MediaReaction, MediaReactionButton


class MediaMessageRepository:
    """Data access object for persisted media messages and delivery state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_message(
        self,
        *,
        telegram_message_id: int,
        telegram_chat_id: int,
        sender_telegram_id: int,
        direction: str,
        media_type: str,
        kalan_id: int,
        date: datetime | None,
        caption: str | None = None,
        recipient_telegram_id: int | None = None,
        sender_id: int | None = None,
        mirrored_from_media_message_id: int | None = None,
    ) -> MediaMessage:
        """Persist metadata for one incoming or outgoing media message."""
        media_message = MediaMessage(
            telegram_message_id=telegram_message_id,
            telegram_chat_id=telegram_chat_id,
            sender_telegram_id=sender_telegram_id,
            recipient_telegram_id=recipient_telegram_id,
            direction=direction,
            media_type=media_type,
            caption=caption,
            date=date,
            sender_id=sender_id,
            kalan_id=kalan_id,
            mirrored_from_media_message_id=mirrored_from_media_message_id,
        )
        self._session.add(media_message)
        await self._session.flush()
        return media_message

    async def create_delivery(
        self,
        *,
        incoming_media_message_id: int,
        recipient_telegram_id: int,
    ) -> MediaDelivery:
        """Create a pending recipient delivery record before Telegram send is attempted."""
        delivery = MediaDelivery(
            incoming_media_message_id=incoming_media_message_id,
            recipient_telegram_id=recipient_telegram_id,
            status="pending",
        )
        self._session.add(delivery)
        await self._session.flush()
        return delivery

    async def mark_delivery_sent(
        self,
        *,
        delivery_id: int,
        outgoing_media_message_id: int,
        telegram_chat_id: int,
        telegram_message_id: int,
    ) -> MediaDelivery:
        """Store Telegram identifiers for a successfully sent delivery."""
        delivery = await self._session.get(MediaDelivery, delivery_id)
        if delivery is None:
            raise ValueError(f"Media delivery {delivery_id} was not found")

        delivery.outgoing_media_message_id = outgoing_media_message_id
        delivery.telegram_chat_id = telegram_chat_id
        delivery.telegram_message_id = telegram_message_id
        delivery.status = "sent"
        await self._session.flush()
        return delivery

    async def mark_delivery_failed(self, *, delivery_id: int, error: str) -> MediaDelivery:
        """Persist a failed delivery status and a compact diagnostic message."""
        delivery = await self._session.get(MediaDelivery, delivery_id)
        if delivery is None:
            raise ValueError(f"Media delivery {delivery_id} was not found")

        delivery.status = "failed"
        delivery.error = error[:512]
        await self._session.flush()
        return delivery

    async def create_reaction_button(
        self,
        *,
        delivery_id: int,
        recipient_telegram_id: int,
        action: str,
        callback_data: str,
    ) -> MediaReactionButton:
        """Persist one recipient-specific inline button callback."""
        button = MediaReactionButton(
            delivery_id=delivery_id,
            recipient_telegram_id=recipient_telegram_id,
            action=action,
            callback_data=callback_data,
        )
        self._session.add(button)
        await self._session.flush()
        return button

    async def get_reaction_button_by_callback_data(
        self, callback_data: str
    ) -> MediaReactionButton | None:
        """Return a stored media reaction button for callback handling after restarts."""
        result = await self._session.execute(
            select(MediaReactionButton).where(MediaReactionButton.callback_data == callback_data)
        )
        return result.scalar_one_or_none()

    async def mark_reaction_button_clicked(
        self, *, callback_data: str
    ) -> MediaReactionButton | None:
        """Mark a stored media reaction button as clicked while callback handling is a stub."""
        button = await self.get_reaction_button_by_callback_data(callback_data)
        if button is None:
            return None

        button.clicked_at = datetime.now(timezone.utc)
        await self._session.flush()
        return button

    async def get_delivery(self, delivery_id: int) -> MediaDelivery | None:
        """Return a media delivery by id."""
        return await self._session.get(MediaDelivery, delivery_id)

    async def get_reaction_button(
        self, *, delivery_id: int, action: str
    ) -> MediaReactionButton | None:
        """Return one stored button for a delivery and action."""
        result = await self._session.execute(
            select(MediaReactionButton).where(
                MediaReactionButton.delivery_id == delivery_id,
                MediaReactionButton.action == action,
            )
        )
        return result.scalar_one_or_none()

    async def get_reaction_choice(
        self, *, delivery_id: int, recipient_telegram_id: int
    ) -> MediaReaction | None:
        """Return a recipient's persisted choice for a delivered media message."""
        result = await self._session.execute(
            select(MediaReaction).where(
                MediaReaction.delivery_id == delivery_id,
                MediaReaction.recipient_telegram_id == recipient_telegram_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_reaction_choice(
        self, *, delivery_id: int, recipient_telegram_id: int, action: str
    ) -> MediaReaction:
        """Persist a recipient's media reaction choice."""
        reaction = MediaReaction(
            delivery_id=delivery_id,
            recipient_telegram_id=recipient_telegram_id,
            action=action,
        )
        self._session.add(reaction)
        await self._session.flush()
        return reaction

    async def delete_reaction_choice(self, reaction: MediaReaction) -> None:
        """Delete a recipient's persisted media reaction choice."""
        await self._session.delete(reaction)
        await self._session.flush()
