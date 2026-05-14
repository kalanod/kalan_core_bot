"""Dependency container factories for the bot runtime."""

from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.bot.config import Settings, get_settings
from app.bot.database import create_database_schema, create_engine, create_session_factory
from app.bot.handlers import setup_routers


@dataclass(frozen=True)
class BotApplication:
    """Runtime objects required to run Telegram polling."""

    bot: Bot
    dispatcher: Dispatcher
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


async def on_startup(dispatcher: Dispatcher, engine: AsyncEngine) -> None:
    """Prepare external resources before polling starts."""
    await create_database_schema(engine)


async def on_shutdown(engine: AsyncEngine) -> None:
    """Release external resources after polling stops."""
    await engine.dispose()


def create_app(settings: Settings | None = None) -> BotApplication:
    """Build runtime dependencies without embedding business logic."""
    resolved_settings = settings or get_settings()
    engine = create_engine(resolved_settings)
    session_factory = create_session_factory(engine)

    bot = Bot(
        token=resolved_settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(session_factory=session_factory, engine=engine)
    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)
    setup_routers(dispatcher)
    return BotApplication(
        bot=bot,
        dispatcher=dispatcher,
        settings=resolved_settings,
        engine=engine,
        session_factory=session_factory,
    )
