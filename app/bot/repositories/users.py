"""Persistence operations for Telegram users."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.database.models import User


class UserRepository:
    """Small data access object for user records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Return a user by Telegram id, if it already exists."""
        result = await self._session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int) -> User:
        """Return an existing user or create a new one with default counters."""
        user = await self.get_by_telegram_id(telegram_id)
        if user is not None:
            return user

        user = User(telegram_id=telegram_id)
        self._session.add(user)
        await self._session.flush()
        return user
