"""Handlers for supported Telegram media messages."""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.services import KalanService
from app.bot.utils.media import extract_kalan_id

router = Router(name="media")


@router.message(F.photo | F.video)
async def handle_media(
    message: Message,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Store incoming photo/video file ids as Kalan records."""
    if message.from_user is None:
        return

    kalan_id = extract_kalan_id(message)
    if kalan_id is None:
        await message.answer("Пока я умею сохранять только фото и видео.")
        return

    async with session_factory() as session:
        result = await KalanService(session).register_media(
            owner_telegram_id=message.from_user.id,
            kalan_id=kalan_id,
        )

    if result.created:
        await message.answer("Калан сохранён ✅")
        return

    await message.answer("Этот калан уже был сохранён ранее.")
