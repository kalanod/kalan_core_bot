"""Database schema lifecycle helpers."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from app.bot.database.models import Base

SOFT_DELETE_COLUMN_TABLES = ("media_messages", "media_deliveries")


async def create_database_schema(engine: AsyncEngine) -> None:
    """Create database tables and lightweight compatibility columns if absent."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_ensure_soft_delete_columns)


def _ensure_soft_delete_columns(connection: Connection) -> None:
    """Add soft-delete columns to existing deployments created before this field existed."""
    inspector = inspect(connection)
    for table_name in SOFT_DELETE_COLUMN_TABLES:
        column_names = {column["name"] for column in inspector.get_columns(table_name)}
        if "is_alive" in column_names:
            continue
        connection.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN is_alive BOOLEAN NOT NULL DEFAULT TRUE")
        )
