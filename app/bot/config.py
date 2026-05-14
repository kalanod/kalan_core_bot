"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.bot.utils.access import parse_allow_list


class Settings(BaseSettings):
    """Typed settings for the Telegram bot and infrastructure."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr = Field(alias="BOT_TOKEN")
    app_env: Literal["local", "dev", "stage", "prod"] = Field(default="local", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="kalan_core_bot", alias="POSTGRES_DB")
    postgres_user: str = Field(default="kalan_core_bot", alias="POSTGRES_USER")
    postgres_password: SecretStr = Field(alias="POSTGRES_PASSWORD")
    database_url: SecretStr = Field(alias="DATABASE_URL")
    allow_list: list[str] = Field(default_factory=list, alias="ALLOW_LIST")

    @property
    def allowed_usernames(self) -> frozenset[str]:
        """Return normalized Telegram usernames allowed to enter onboarding."""
        return parse_allow_list(self.allow_list)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
