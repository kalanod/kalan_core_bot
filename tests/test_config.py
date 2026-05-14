"""Configuration smoke tests."""

from app.bot.config import Settings


def test_settings_can_be_created_from_values() -> None:
    settings = Settings(
        BOT_TOKEN="123456:test-token",
        POSTGRES_PASSWORD="test-password",
        DATABASE_URL="postgresql+asyncpg://user:password@postgres:5432/app",
    )

    assert settings.app_env == "local"
    assert settings.postgres_host == "postgres"
    assert settings.bot_token.get_secret_value() == "123456:test-token"
    assert settings.allowed_usernames == frozenset()


def test_settings_parses_allow_list_from_values() -> None:
    settings = Settings(
        BOT_TOKEN="123456:test-token",
        POSTGRES_PASSWORD="test-password",
        DATABASE_URL="postgresql+asyncpg://user:password@postgres:5432/app",
        ALLOW_LIST=["@Alice", "bob"],
    )

    assert settings.allowed_usernames == {"alice", "bob"}


def test_settings_parses_allow_list_from_json_env(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "123456:test-token")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:password@postgres:5432/app")
    monkeypatch.setenv("ALLOW_LIST", '["@Alice", "bob"]')

    settings = Settings()

    assert settings.allowed_usernames == {"alice", "bob"}
