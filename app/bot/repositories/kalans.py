"""Persistence operations for Kalan media records."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.database.models import Kalan


class KalanRepository:
    """Small data access object for media records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_kalan_id(self, kalan_id: str) -> Kalan | None:
        """Return a media record by Telegram file id, if present."""
        result = await self._session.execute(select(Kalan).where(Kalan.kalan_id == kalan_id))
        return result.scalar_one_or_none()

    async def create(self, *, kalan_id: str, owner_id: int) -> Kalan:
        """Create a new alive media record owned by the provided user id."""
        kalan = Kalan(kalan_id=kalan_id, owner_id=owner_id)
        self._session.add(kalan)
        await self._session.flush()
        return kalan

    async def get_or_create_alive(self, *, kalan_id: str, owner_id: int) -> Kalan:
        """Return an existing media record or create it as alive for the owner."""
        kalan = await self.get_by_kalan_id(kalan_id)
        if kalan is not None:
            if kalan.owner_id == owner_id and not kalan.is_alive:
                kalan.is_alive = True
                await self._session.flush()
            return kalan

        return await self.create(kalan_id=kalan_id, owner_id=owner_id)

    async def mark_deleted_by_owner(self, *, kalan_id: str, owner_id: int) -> Kalan | None:
        """Mark media as not alive only when the provided user owns it."""
        result = await self._session.execute(
            select(Kalan).where(Kalan.kalan_id == kalan_id, Kalan.owner_id == owner_id)
        )
        kalan = result.scalar_one_or_none()
        if kalan is None:
            return None

        kalan.is_alive = False
        await self._session.flush()
        return kalan
