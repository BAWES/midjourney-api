"""Discord Interaction API for triggering Midjourney /imagine and button clicks."""

import asyncio
import random
import time

import httpx

MJ_APP_ID = "936929561302675456"
DISCORD_API = "https://discord.com/api/v10"
COMMAND_CACHE_TTL = 3600


class InteractionClient:
    def __init__(self, user_token: str, channel_id: str) -> None:
        self._user_token = user_token
        self._channel_id = channel_id
        self._http: httpx.AsyncClient | None = None
        self._guild_id: str | None = None
        self._command_cache: dict | None = None
        self._cache_time: float = 0.0

    async def start(self) -> None:
        self._http = httpx.AsyncClient(timeout=30)

    async def stop(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    async def get_guild_id(self) -> str:
        if self._guild_id:
            return self._guild_id
        assert self._http is not None
        resp = await self._http.get(
            f"{DISCORD_API}/channels/{self._channel_id}",
            headers={"Authorization": self._user_token},
        )
        resp.raise_for_status()
        self._guild_id = resp.json()["guild_id"]
        return self._guild_id

    async def get_imagine_command(self, force_refresh: bool = False) -> dict:
        cache_expired = (time.monotonic() - self._cache_time) > COMMAND_CACHE_TTL
        if self._command_cache and not force_refresh and not cache_expired:
            return self._command_cache
        assert self._http is not None
        guild_id = await self.get_guild_id()
        resp = await self._http.get(
            f"{DISCORD_API}/guilds/{guild_id}/application-command-index",
            headers={"Authorization": self._user_token},
        )
        resp.raise_for_status()
        data = resp.json()
        for cmd in data.get("application_commands", []):
            if cmd.get("name") == "imagine" and cmd.get("application_id") == MJ_APP_ID:
                self._command_cache = cmd
                self._cache_time = time.monotonic()
                return cmd
        raise RuntimeError("Midjourney /imagine command not found in guild")

    async def send_imagine(self, prompt: str) -> int:
        """Send /imagine command. Returns HTTP status code."""
        assert self._http is not None
        guild_id = await self.get_guild_id()
        command = await self.get_imagine_command()

        delay = random.uniform(1.0, 3.0)
        await asyncio.sleep(delay)

        payload = {
            "type": 2,
            "application_id": MJ_APP_ID,
            "guild_id": guild_id,
            "channel_id": self._channel_id,
            "session_id": str(random.randint(100000, 999999)),
            "data": {
                "version": command["version"],
                "id": command["id"],
                "name": "imagine",
                "type": 1,
                "options": [
                    {"type": 3, "name": "prompt", "value": prompt}
                ],
                "application_command": {
                    "id": command["id"],
                    "application_id": MJ_APP_ID,
                    "version": command["version"],
                    "type": 1,
                    "name": "imagine",
                    "options": [
                        {
                            "type": 3,
                            "name": "prompt",
                            "description": "The prompt to imagine",
                            "required": True,
                        }
                    ],
                },
                "attachments": [],
            },
        }

        resp = await self._http.post(
            f"{DISCORD_API}/interactions",
            json=payload,
            headers={
                "Authorization": self._user_token,
                "Content-Type": "application/json",
            },
        )
        return resp.status_code

    async def send_component_interaction(self, message_id: str, custom_id: str) -> int:
        """Click a button (upscale, vary, reroll, animate, etc.) on a message."""
        assert self._http is not None
        guild_id = await self.get_guild_id()

        delay = random.uniform(1.0, 2.0)
        await asyncio.sleep(delay)

        payload = {
            "type": 3,
            "guild_id": guild_id,
            "channel_id": self._channel_id,
            "message_id": message_id,
            "application_id": MJ_APP_ID,
            "session_id": str(random.randint(100000, 999999)),
            "data": {
                "component_type": 2,
                "custom_id": custom_id,
            },
        }

        resp = await self._http.post(
            f"{DISCORD_API}/interactions",
            json=payload,
            headers={
                "Authorization": self._user_token,
                "Content-Type": "application/json",
            },
        )
        return resp.status_code

    def invalidate_command_cache(self) -> None:
        self._command_cache = None
        self._cache_time = 0.0
