"""Business operations for media fan-out broadcasts and reaction callbacks."""

import secrets
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.database.models import Kalan, MediaDelivery, MediaMessage, MediaReactionButton, User
from app.bot.keyboards.media import OTTER_ACTION, STONE_FACE_ACTION, UNDO_REACTION_ACTION
from app.bot.repositories import KalanRepository, MediaMessageRepository, UserRepository

REACTION_ACTIONS = {OTTER_ACTION, STONE_FACE_ACTION}


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


@dataclass(frozen=True)
class MediaReactionToggleResult:
    """State needed by handlers after a media reaction callback is applied."""

    status: str
    action: str | None = None
    approves: int = 0
    declines: int = 0
    otter_callback_data: str | None = None
    stone_face_callback_data: str | None = None
    undo_callback_data: str | None = None


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
        """Persist a delivery package and recipient-specific button callback data."""
        delivery = await self._media_messages.create_delivery(
            incoming_media_message_id=incoming_media_message_id,
            recipient_telegram_id=recipient_telegram_id,
        )
        otter_callback_data = self._build_callback_data(delivery.id, OTTER_ACTION)
        stone_face_callback_data = self._build_callback_data(delivery.id, STONE_FACE_ACTION)
        undo_callback_data = self._build_callback_data(delivery.id, UNDO_REACTION_ACTION)
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
        await self._media_messages.create_reaction_button(
            delivery_id=delivery.id,
            recipient_telegram_id=recipient_telegram_id,
            action=UNDO_REACTION_ACTION,
            callback_data=undo_callback_data,
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
    ) -> MediaReactionToggleResult:
        """Apply or undo a recipient media reaction and return the keyboard state to show."""
        button = await self._media_messages.get_reaction_button_by_callback_data(callback_data)
        if button is None or button.recipient_telegram_id != user_telegram_id:
            await self._session.commit()
            return MediaReactionToggleResult(status="not_found")

        if button.action not in REACTION_ACTIONS | {UNDO_REACTION_ACTION}:
            await self._session.commit()
            return MediaReactionToggleResult(status="not_found")

        await self._media_messages.mark_reaction_button_clicked(callback_data=callback_data)
        delivery = await self._media_messages.get_delivery(button.delivery_id)
        if delivery is None:
            await self._session.commit()
            return MediaReactionToggleResult(status="not_found")

        media_message = await self._session.get(MediaMessage, delivery.incoming_media_message_id)
        if media_message is None:
            await self._session.commit()
            return MediaReactionToggleResult(status="not_found")

        kalan = await self._session.get(Kalan, media_message.kalan_id)
        if kalan is None:
            await self._session.commit()
            return MediaReactionToggleResult(status="not_found")

        existing_reaction = await self._media_messages.get_reaction_choice(
            delivery_id=delivery.id,
            recipient_telegram_id=user_telegram_id,
        )
        if existing_reaction is not None:
            cancelled_action = existing_reaction.action
            await self._apply_counter_delta(kalan=kalan, action=cancelled_action, delta=-1)
            await self._media_messages.delete_reaction_choice(existing_reaction)
            otter_button = await self._required_button(delivery.id, OTTER_ACTION)
            stone_face_button = await self._required_button(delivery.id, STONE_FACE_ACTION)
            await self._session.commit()
            return MediaReactionToggleResult(
                status="cancelled",
                action=cancelled_action,
                approves=kalan.approves,
                declines=kalan.rejects,
                otter_callback_data=otter_button.callback_data,
                stone_face_callback_data=stone_face_button.callback_data,
            )

        if button.action == UNDO_REACTION_ACTION:
            await self._session.commit()
            return MediaReactionToggleResult(
                status="unchanged",
                approves=kalan.approves,
                declines=kalan.rejects,
            )

        await self._media_messages.create_reaction_choice(
            delivery_id=delivery.id,
            recipient_telegram_id=user_telegram_id,
            action=button.action,
        )
        await self._apply_counter_delta(kalan=kalan, action=button.action, delta=1)
        undo_button = await self._get_or_create_button(
            delivery=delivery,
            recipient_telegram_id=user_telegram_id,
            action=UNDO_REACTION_ACTION,
        )
        await self._session.commit()
        return MediaReactionToggleResult(
            status="applied",
            action=button.action,
            approves=kalan.approves,
            declines=kalan.rejects,
            undo_callback_data=undo_button.callback_data,
        )

    async def _required_button(self, delivery_id: int, action: str) -> MediaReactionButton:
        """Return an existing delivery button or raise if persisted state is inconsistent."""
        button = await self._media_messages.get_reaction_button(
            delivery_id=delivery_id,
            action=action,
        )
        if button is None:
            raise ValueError(
                f"Media reaction button {action!r} for delivery {delivery_id} was not found"
            )
        return button

    async def _get_or_create_button(
        self, *, delivery: MediaDelivery, recipient_telegram_id: int, action: str
    ) -> MediaReactionButton:
        """Return an existing delivery button or create it for messages sent by older code."""
        button = await self._media_messages.get_reaction_button(
            delivery_id=delivery.id,
            action=action,
        )
        if button is not None:
            return button

        return await self._media_messages.create_reaction_button(
            delivery_id=delivery.id,
            recipient_telegram_id=recipient_telegram_id,
            action=action,
            callback_data=self._build_callback_data(delivery.id, action),
        )

    async def _apply_counter_delta(self, *, kalan: Kalan, action: str, delta: int) -> None:
        """Adjust media counters and the media owner's aggregate counters."""
        owner = await self._session.get(User, kalan.owner_id)
        if action == OTTER_ACTION:
            kalan.approves = max(0, kalan.approves + delta)
            if owner is not None:
                owner.approves = max(0, owner.approves + delta)
        elif action == STONE_FACE_ACTION:
            kalan.rejects = max(0, kalan.rejects + delta)
            if owner is not None:
                owner.rejects = max(0, owner.rejects + delta)
        await self._session.flush()

    @staticmethod
    def _build_callback_data(delivery_id: int, action: str) -> str:
        """Build compact callback data that fits Telegram's 64-byte callback_data limit."""
        return f"mr:{delivery_id}:{action}:{secrets.token_urlsafe(6)}"
