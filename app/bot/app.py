"""Telegram bot bootstrap module."""

import asyncio

from app.bot.container import create_app


async def main() -> None:
    """Create dependencies and start Telegram polling."""
    application = create_app()
    await application.dispatcher.start_polling(application.bot)


def run_bot() -> None:
    """Run the bot application from a synchronous entry point."""
    asyncio.run(main())
