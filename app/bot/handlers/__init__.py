"""Router registration for Telegram update handlers."""

from aiogram import Dispatcher, Router

from app.bot.handlers import health, media, start, text


def setup_routers(dispatcher: Dispatcher) -> None:
    """Attach feature routers to the root dispatcher."""
    root_router = Router(name="root")
    root_router.include_router(health.router)
    root_router.include_router(start.router)
    root_router.include_router(media.router)
    root_router.include_router(text.router)
    dispatcher.include_router(root_router)
