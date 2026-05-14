"""Handlers for Telegram bot commands."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="commands")

KALAN_COMMAND_RESPONSE = "купи калану котлеты"


@router.message(Command("kalan"))
async def handle_kalan_command(message: Message) -> None:
    """Reply to the hidden /kalan command without broadcasting it as user text."""
    await message.answer(KALAN_COMMAND_RESPONSE)
