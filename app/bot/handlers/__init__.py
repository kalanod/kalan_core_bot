"""Router registration for Telegram update handlers."""

from aiogram import Dispatcher, Router

from app.bot.handlers import health, start


def setup_routers(dispatcher: Dispatcher) -> None:
    """Attach feature routers to the root dispatcher."""
    root_router = Router(name="root")
    root_router.include_router(health.router)
    root_router.include_router(start.router)
    dispatcher.include_router(root_router)
