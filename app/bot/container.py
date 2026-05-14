"""Dependency container factories for the bot runtime."""

from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.config import Settings, get_settings
from app.bot.handlers import setup_routers


@dataclass(frozen=True)
class BotApplication:
    """Runtime objects required to run Telegram polling."""

    bot: Bot
    dispatcher: Dispatcher
    settings: Settings


def create_app(settings: Settings | None = None) -> BotApplication:
    """Build runtime dependencies without embedding business logic."""
    resolved_settings = settings or get_settings()
    bot = Bot(
        token=resolved_settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    setup_routers(dispatcher)
    return BotApplication(bot=bot, dispatcher=dispatcher, settings=resolved_settings)
