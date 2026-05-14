"""Start command handlers."""

from pathlib import Path

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.keyboards.start import ACCEPT_CLUB_VALUE_CALLBACK_DATA, build_start_accept_keyboard
from app.bot.services import UserService, UserStore

router = Router(name="start")

START_IMAGE_PATH = Path(__file__).resolve().parents[2] / "static" / "images" / "init.png"
START_MESSAGE = (
    "Добро пожаловать в летнюю коллекцию калан core, стань частью клуба анонимных "
    "каланистов и создай за эти 3 месяца нашу коллекцию\n"
    "Отправляй в бота любые картинки или видео, про которые скажешь \"о да, это калан core\" "
    "и их тут же получат все другие участники проекта, общайся и оценивай находки друзей.\n"
    "Любая картинка что наберёт больше 80% каланности попадёт да доску проекта после окончания\n\n"
    "Но помни! Всё общение в проекте полностью анонимно, никто не знает вашего имени (даже Андрей), "
    "для продолжения требуется принять ценность.\n\n"
    "Торжественно обещаю, я проведу это лето ярко!"
)
WELCOME_MESSAGE = "добро пожаловать в клуб"


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Show the onboarding screen without registering the Telegram user."""
    await message.answer_photo(
        photo=FSInputFile(START_IMAGE_PATH),
        caption=START_MESSAGE,
        reply_markup=build_start_accept_keyboard(),
    )


@router.callback_query(F.data == ACCEPT_CLUB_VALUE_CALLBACK_DATA)
async def handle_start_accept_callback(
    callback: CallbackQuery,
    session_factory: async_sessionmaker[AsyncSession],
    user_store: UserStore,
) -> None:
    """Register the Telegram user only after they accept the club value."""
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)

    async with session_factory() as session:
        await UserService(session).ensure_registered(telegram_id=callback.from_user.id)
    await user_store.add_user(callback.from_user.id)

    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(WELCOME_MESSAGE)
