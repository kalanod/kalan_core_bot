# kalan_core_bot

Telegram bot service for Kalan Core.

## Architecture

The project is prepared as a production-oriented Python Telegram bot skeleton without business logic yet:

- `app/main.py` — container entry point.
- `app/bot/config.py` — typed settings loaded from `.env`.
- `app/bot/container.py` — runtime dependency wiring for aiogram.
- `app/bot/handlers/` — Telegram routers grouped by feature.
- `app/bot/services/` — future business logic layer.
- `app/bot/repositories/` — future database access layer.
- `app/bot/database/` — SQLAlchemy engine, sessions, models, and migrations.
- `app/bot/middlewares/`, `app/bot/keyboards/`, `app/bot/utils/` — dedicated extension points.

## Local start

1. Copy environment template:

   ```bash
   cp .env_template .env
   ```

2. Fill `BOT_TOKEN`, `POSTGRES_PASSWORD`, and `DATABASE_URL` in `.env`.
3. Start the bot and PostgreSQL:

   ```bash
   docker compose up --build
   ```

## Development checks

```bash
python -m compileall app tests
pytest
```
