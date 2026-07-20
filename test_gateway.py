#!/usr/bin/env python3
"""Quick test: try connecting to Discord with the bot token."""
import asyncio
import discord
import os
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get("DISCORD_BOT_TOKEN", "")
print(f"Token loaded: {token[:10]}...{token[-5:]}" if token else "NO TOKEN LOADED")

intents = discord.Intents.default()
intents.message_content = True


async def test():
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"CONNECTED! Bot: {client.user} (ID: {client.user.id})")
        await client.close()

    @client.event
    async def on_error(event, *args, **kwargs):
        print(f"ERROR in {event}: {args} {kwargs}")

    try:
        await client.start(token)
    except discord.LoginFailure:
        print("LOGIN FAILED: Invalid bot token")
    except Exception as e:
        print(f"CONNECTION ERROR: {type(e).__name__}: {e}")


asyncio.run(test())
