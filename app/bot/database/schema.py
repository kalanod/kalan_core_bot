"""Database schema lifecycle helpers."""

from sqlalchemy.ext.asyncio import AsyncEngine

from app.bot.database.models import Base


async def create_database_schema(engine: AsyncEngine) -> None:
    """Create database tables declared in ORM metadata if they do not exist."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
