"""SQLAlchemy ORM model declarations."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
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
