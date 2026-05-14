"""Start command handlers."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.config import Settings
from app.bot.keyboards.start import ACCEPT_CLUB_VALUE_CALLBACK_DATA, build_start_accept_keyboard
from app.bot.services import UserService, UserStore
from app.bot.utils.access import is_username_allowed

router = Router(name="start")

START_IMAGE_PATH = Path(__file__).resolve().parents[2] / "static" / "images" / "init.jpg"
RESTRICTED_IMAGE_PATH = Path(__file__).resolve().parents[2] / "static" / "images" / "restricted.png"
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
PROJECT_END_DATE = date(2026, 9, 1)


@dataclass(frozen=True)
class StartScreen:
    """Resolved first-message payload for a Telegram user."""

    image_path: Path
    caption: str | None
    reply_markup: InlineKeyboardMarkup | None


def build_start_screen(username: str | None, allow_list: Iterable[str]) -> StartScreen:
    """Build the onboarding screen that matches the user's allow-list status."""
    if is_username_allowed(username, allow_list):
        return StartScreen(
            image_path=START_IMAGE_PATH,
            caption=START_MESSAGE,
            reply_markup=build_start_accept_keyboard(),
        )

    return StartScreen(image_path=RESTRICTED_IMAGE_PATH, caption=None, reply_markup=None)


def build_days_left_message(today: date | None = None) -> str:
    """Build the status message for users who have already accepted the club value."""
    current_date = today or datetime.now(UTC).date()
    days_left = max((PROJECT_END_DATE - current_date).days, 0)
    return f"до конца {days_left} дней"


async def delete_previous_start_messages(
    *,
    message: Message,
    user_store: UserStore,
    telegram_id: int,
) -> None:
    """Best-effort delete previously sent onboarding prompts for this user."""
    start_messages = await user_store.pop_start_messages(telegram_id)
    for chat_id, message_id in start_messages:
        try:
            await message.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramAPIError:
            continue


async def send_start_screen(message: Message, start_screen: StartScreen) -> Message:
    """Send a resolved onboarding or restricted screen."""
    return await message.answer_photo(
        photo=FSInputFile(start_screen.image_path),
        caption=start_screen.caption,
        reply_markup=start_screen.reply_markup,
    )


@router.message(CommandStart())
async def handle_start(
    message: Message,
    user_store: UserStore,
    settings: Settings,
) -> None:
    """Show onboarding only to allowed users and status to registered users."""
    if message.from_user is None:
        return

    telegram_id = message.from_user.id
    if await user_store.has_user(telegram_id):
        await message.answer(build_days_left_message())
        return

    await delete_previous_start_messages(
        message=message,
        user_store=user_store,
        telegram_id=telegram_id,
    )
    start_screen = build_start_screen(message.from_user.username, settings.allowed_usernames)
    sent_message = await send_start_screen(message, start_screen)
    await user_store.remember_start_message(
        telegram_id=telegram_id,
        chat_id=sent_message.chat.id,
        message_id=sent_message.message_id,
    )


@router.callback_query(F.data == ACCEPT_CLUB_VALUE_CALLBACK_DATA)
async def handle_start_accept_callback(
    callback: CallbackQuery,
    session_factory: async_sessionmaker[AsyncSession],
    user_store: UserStore,
    settings: Settings,
) -> None:
    """Register the Telegram user only after an allowed username accepts the club value."""
    if not is_username_allowed(callback.from_user.username, settings.allowed_usernames):
        await callback.answer()
        if callback.message is not None:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer_photo(photo=FSInputFile(RESTRICTED_IMAGE_PATH))
        return

    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await user_store.pop_start_messages(callback.from_user.id)

    async with session_factory() as session:
        await UserService(session).ensure_registered(telegram_id=callback.from_user.id)
    await user_store.add_user(callback.from_user.id)

    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(WELCOME_MESSAGE)
