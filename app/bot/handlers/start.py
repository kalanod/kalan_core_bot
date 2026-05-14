"""Start command handlers."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.services import UserService, UserStore

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(
    message: Message,
    session_factory: async_sessionmaker[AsyncSession],
    user_store: UserStore,
) -> None:
    """Register a Telegram user and greet them."""
    if message.from_user is None:
        return

    async with session_factory() as session:
        result = await UserService(session).ensure_registered(telegram_id=message.from_user.id)
    await user_store.add_user(message.from_user.id)

    greeting = "Добро пожаловать!" if result.created else "Рады видеть снова!"
    await message.answer(
        f"{greeting}\n"
        "Отправь фото или видео — я сохраню media id как kalan_id для дальнейшей работы."
    )
