#!/bin/bash
# Watchdog for midjourney-mcp server.
# Checks every 2 minutes if the server is running, restarts if dead.

MCP_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_LOG="$MCP_DIR/midjourney_mcp.log"

cd "$MCP_DIR" || exit 1

if ! pgrep -f "run.py" > /dev/null 2>&1; then
    echo "[$(date)] MJ-MCP not running, starting..." >> "$MCP_LOG"
    source venv/bin/activate
    export $(grep -v '^#' .env | xargs)
    nohup python3 run.py >> "$MCP_LOG" 2>&1 &
    echo "[$(date)] Started PID $!" >> "$MCP_LOG"
fi
