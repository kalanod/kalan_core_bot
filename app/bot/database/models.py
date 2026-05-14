"""SQLAlchemy ORM model declarations."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class User(Base):
    """Telegram user persisted by the bot."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    approves: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    rejects: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    kalans: Mapped[list["Kalan"]] = relationship(back_populates="owner")
    text_messages: Mapped[list["TextMessage"]] = relationship(
        back_populates="sender",
        foreign_keys="TextMessage.sender_id",
    )
    media_messages: Mapped[list["MediaMessage"]] = relationship(
        back_populates="sender",
        foreign_keys="MediaMessage.sender_id",
    )


class Kalan(Base):
    """Media item sent to the bot and available for later reuse."""

    __tablename__ = "kalans"

    id: Mapped[int] = mapped_column(primary_key=True)
    kalan_id: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    approves: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    rejects: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    owner: Mapped[User] = relationship(back_populates="kalans")
    media_messages: Mapped[list["MediaMessage"]] = relationship(back_populates="kalan")


class MediaMessage(Base):
    """Telegram media message metadata persisted for fan-out broadcasts."""

    __tablename__ = "media_messages"
    __table_args__ = (
        UniqueConstraint(
            "telegram_chat_id",
            "telegram_message_id",
            name="uq_media_messages_chat_message",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sender_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    recipient_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sender_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    kalan_id: Mapped[int] = mapped_column(ForeignKey("kalans.id", ondelete="CASCADE"), nullable=False)
    mirrored_from_media_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    sender: Mapped[User | None] = relationship(
        back_populates="media_messages",
        foreign_keys=[sender_id],
    )
    kalan: Mapped[Kalan] = relationship(back_populates="media_messages")


class MediaDelivery(Base):
    """Per-recipient state for a media package sent by the bot."""

    __tablename__ = "media_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "incoming_media_message_id",
            "recipient_telegram_id",
            name="uq_media_deliveries_incoming_recipient",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    incoming_media_message_id: Mapped[int] = mapped_column(
        ForeignKey("media_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    outgoing_media_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipient_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MediaReactionButton(Base):
    """Persisted recipient-specific inline button for media reaction callbacks."""

    __tablename__ = "media_reaction_buttons"
    __table_args__ = (
        UniqueConstraint("delivery_id", "action", name="uq_media_buttons_delivery_action"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[int] = mapped_column(
        ForeignKey("media_deliveries.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    callback_data: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MediaReaction(Base):
    """Persisted recipient choice for a delivered media message."""

    __tablename__ = "media_reactions"
    __table_args__ = (
        UniqueConstraint(
            "delivery_id",
            "recipient_telegram_id",
            name="uq_media_reactions_delivery_recipient",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[int] = mapped_column(
        ForeignKey("media_deliveries.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TextMessage(Base):
    """Telegram text message metadata persisted for broadcast and reply tracking."""

    __tablename__ = "text_messages"
    __table_args__ = (
        UniqueConstraint(
            "telegram_chat_id",
            "telegram_message_id",
            name="uq_text_messages_chat_message",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sender_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    recipient_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sender_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reply_to_text_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("text_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    mirrored_from_text_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("text_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    sender: Mapped[User | None] = relationship(
        back_populates="text_messages",
        foreign_keys=[sender_id],
    )
