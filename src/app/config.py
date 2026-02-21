from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/midjourney_api"

    # Discord Bot (Gateway monitoring)
    discord_bot_token: str = ""

    # Discord User Token (Interaction API)
    discord_user_token: str = ""

    # Midjourney channel
    mj_channel_id: str = ""

    # Midjourney concurrency (Standard=3, Pro=12)
    mj_max_concurrent_jobs: int = 3

    # Task timeout in seconds
    mj_task_timeout_seconds: int = 120

    # Quota: platform-wide daily limit
    platform_daily_limit: int = 100

    # API
    api_v1_prefix: str = "/api/v1"


settings = Settings()
