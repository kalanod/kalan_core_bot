"""Database schema lifecycle helpers."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from app.bot.database.models import Base

SOFT_DELETE_COLUMN_TABLES = ("media_messages", "media_deliveries")
TEXT_MESSAGE_COMPAT_COLUMNS = {
    "recipient_telegram_id": "BIGINT",
    "reply_to_text_message_id": "INTEGER REFERENCES text_messages(id) ON DELETE SET NULL",
    "mirrored_from_text_message_id": "INTEGER REFERENCES text_messages(id) ON DELETE SET NULL",
}


async def create_database_schema(engine: AsyncEngine) -> None:
    """Create database tables and lightweight compatibility columns if absent."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_ensure_soft_delete_columns)
        await connection.run_sync(_ensure_text_message_reply_columns)


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


def _ensure_text_message_reply_columns(connection: Connection) -> None:
    """Add text reply-tracking columns to deployments created before threading support."""
    inspector = inspect(connection)
    if "text_messages" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("text_messages")}
    for column_name, column_type in TEXT_MESSAGE_COMPAT_COLUMNS.items():
        if column_name in column_names:
            continue
        connection.execute(
            text(f"ALTER TABLE text_messages ADD COLUMN {column_name} {column_type}")
        )
