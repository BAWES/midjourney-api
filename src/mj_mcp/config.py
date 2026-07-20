from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Discord Bot (Gateway monitoring — discord.py WebSocket)
    discord_bot_token: str = ""

    # Discord User Token (Interaction API — sends /imagine, clicks buttons)
    discord_user_token: str = ""

    # Discord channel where Midjourney bot is installed
    mj_channel_id: str = ""

    # Midjourney concurrency (Standard=3, Pro/Mega=12)
    mj_max_concurrent_jobs: int = 3

    # Generation timeout in seconds
    generation_timeout_seconds: int = 120

    # Auth token for Universe bot MCP calls
    mcp_auth_token: str = ""


settings = Settings()
