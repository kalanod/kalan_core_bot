"""Health check command handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.services import UserStore

router = Router(name="health")


@router.message(Command("health"))
async def handle_health(message: Message, user_store: UserStore) -> None:
    """Respond with a simple liveness message for registered users only."""
    if message.from_user is None or not await user_store.has_user(message.from_user.id):
        return

    await message.answer("OK")
