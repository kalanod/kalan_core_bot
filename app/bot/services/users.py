"""Business operations related to bot users."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.database.models import User
from app.bot.repositories import UserRepository


@dataclass(frozen=True)
class UserRegistrationResult:
    """Result returned after ensuring that a Telegram user exists."""

    user: User
    created: bool


class UserService:
    """Application service for user registration and lookup flows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)

    async def ensure_registered(self, *, telegram_id: int) -> UserRegistrationResult:
        """Persist a Telegram user if needed and return the registration result."""
        existing_user = await self._users.get_by_telegram_id(telegram_id)
        if existing_user is not None:
            return UserRegistrationResult(user=existing_user, created=False)

        user = await self._users.get_or_create(telegram_id)
        await self._session.commit()
        return UserRegistrationResult(user=user, created=True)
