"""Health check command handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="health")


@router.message(Command("health"))
async def handle_health(message: Message) -> None:
    """Respond with a simple liveness message."""
    await message.answer("OK")
