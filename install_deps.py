#!/usr/bin/env python3
"""Install Midjourney MCP server dependencies."""
import subprocess
import sys

deps = [
    "mcp>=1.0.0",
    "discord.py>=2.4.0",
    "httpx>=0.28.0",
    "pydantic-settings>=2.7.0",
    "python-dotenv>=1.0.0",
]

subprocess.check_call([sys.executable, "-m", "pip", "install"] + deps)
print("Done. Run with: python run.py")
