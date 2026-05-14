"""Business operations related to Kalan media."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.database.models import Kalan
from app.bot.repositories import KalanRepository, UserRepository


@dataclass(frozen=True)
class KalanRegistrationResult:
    """Result returned after storing a Telegram media id."""

    kalan: Kalan
    created: bool


@dataclass(frozen=True)
class KalanDeletionResult:
    """Result returned after trying to mark media as deleted by its owner."""

    kalan: Kalan | None
    deleted: bool


class KalanService:
    """Application service for media registration and lifecycle changes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._kalans = KalanRepository(session)

    async def register_media(self, *, owner_telegram_id: int, kalan_id: str) -> KalanRegistrationResult:
        """Persist a photo/video file id as a Kalan owned by the Telegram user."""
        owner = await self._users.get_or_create(owner_telegram_id)
        existing_kalan = await self._kalans.get_by_kalan_id(kalan_id)
        if existing_kalan is not None:
            await self._session.commit()
            return KalanRegistrationResult(kalan=existing_kalan, created=False)

        kalan = await self._kalans.create(kalan_id=kalan_id, owner_id=owner.id)
        await self._session.commit()
        return KalanRegistrationResult(kalan=kalan, created=True)

    async def mark_media_deleted_by_owner(
        self, *, owner_telegram_id: int, kalan_id: str
    ) -> KalanDeletionResult:
        """Mark a Kalan as not alive when deletion is reported by its owner."""
        owner = await self._users.get_by_telegram_id(owner_telegram_id)
        if owner is None:
            return KalanDeletionResult(kalan=None, deleted=False)

        kalan = await self._kalans.mark_deleted_by_owner(kalan_id=kalan_id, owner_id=owner.id)
        await self._session.commit()
        return KalanDeletionResult(kalan=kalan, deleted=kalan is not None)
