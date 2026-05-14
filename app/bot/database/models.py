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
