<div align="center">

# 🎨 Midjourney Relay API

**Programmatic Midjourney image generation through a clean REST API**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![SQLAlchemy 2.x](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://sqlalchemy.org)
[![Discord.py](https://img.shields.io/badge/discord.py-2.4+-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discordpy.readthedocs.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-Private-red?style=for-the-badge)](LICENSE)

<br />

[English](README.md) · [繁體中文](README.zh-TW.md)

---

*Submit a prompt, get back high-resolution images — no Discord client needed.*

</div>

<br />

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [License](#license)

## Overview

Midjourney Relay API bridges the gap between your applications and Midjourney's image generation capabilities. Since Midjourney operates exclusively through Discord, this API automates the entire interaction — sending `/imagine` commands, tracking generation progress, performing auto-upscale, and delivering high-resolution image URLs — all through a simple REST interface.

### Key Features

- **RESTful API** — Submit prompts and poll for results via standard HTTP
- **Auto-Upscale** — Automatically upscale generated images (1–4 images per grid)
- **Concurrency Control** — Respects Midjourney's concurrent job limits (Standard: 3 / Pro: 12)
- **Quota Management** — Daily, monthly, and platform-wide rate limiting with atomic enforcement
- **Multi-tenant** — API key authentication with per-key quota tracking
- **Async-first** — Built entirely on async/await for maximum throughput
- **Provider Abstraction** — Protocol-based design allows swapping Discord for future providers
- **Correlation Tracking** — Embeds unique tags in prompts to reliably match responses

## Architecture

```
                         ┌─────────────────────────────────────────────┐
                         │              Midjourney Relay API           │
                         │                                             │
  Client App             │  ┌─────────┐    ┌──────────┐               │
  ─────────────────►     │  │ FastAPI  │───►│ Services │               │
  POST /api/v1/imagine   │  │ Routes   │    │  Layer   │               │
  X-API-Key: xxx         │  └────┬─────┘    └────┬─────┘               │
                         │       │               │                     │
                         │  ┌────▼─────┐    ┌────▼──────────────┐      │
                         │  │ API Key  │    │ ConcurrencyLimiter│      │
                         │  │  Auth    │    │ (Semaphore Queue) │      │
                         │  └──────────┘    └────┬──────────────┘      │
                         │                       │                     │
                         │            ┌──────────▼──────────┐          │
                         │            │  Discord Provider    │          │
                         │            │ ┌─────────────────┐ │          │
                         │            │ │InteractionClient│──────────────►  Discord API
                         │            │ │ (send /imagine) │ │          │    (Midjourney Bot)
                         │            │ └─────────────────┘ │          │
                         │            │ ┌─────────────────┐ │          │
                         │            │ │ GatewayMonitor  │◄──────────────  Discord Gateway
                         │            │ │(track responses)│ │          │    (WebSocket)
                         │            │ └─────────────────┘ │          │
                         │            └─────────────────────┘          │
                         │                       │                     │
                         │            ┌──────────▼──────────┐          │
                         │            │    PostgreSQL 16     │          │
                         │            │  Tasks · Quota · Logs│          │
                         │            └─────────────────────┘          │
                         └─────────────────────────────────────────────┘
```

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Provider Protocol** | `MidjourneyClient` interface decouples business logic from Discord; enables testing with `MockClient` and future provider swaps |
| **Correlation Tags** | Embeds `mjr-{uuid}` in prompts to match Midjourney's async responses back to tasks |
| **Semaphore Queue** | `asyncio.Semaphore` enforces Midjourney's concurrent job limit without overloading Discord |
| **Atomic Quota** | PostgreSQL row-level locking (`SELECT ... FOR UPDATE`) prevents race conditions |
| **Async-only** | FastAPI + SQLAlchemy async + httpx — zero blocking I/O in the entire stack |

## Prerequisites

Before setting up the API, you need to complete the following steps:

### 1. Subscribe to a Midjourney Plan

1. Go to [midjourney.com](https://www.midjourney.com/)
2. Sign in and subscribe to a plan:
   - **Basic** ($10/mo) — ~200 generations, 3 concurrent jobs
   - **Standard** ($30/mo) — 15h Fast, unlimited Relax, 3 concurrent jobs
   - **Pro** ($60/mo) — 30h Fast, unlimited Relax, **12 concurrent jobs**
   - **Mega** ($120/mo) — 60h Fast, unlimited Relax, **12 concurrent jobs**

> **Recommended:** Standard or Pro plan. The `MJ_MAX_CONCURRENT_JOBS` config should match your plan's limit.

### 2. Create a Discord Server

1. Open [Discord](https://discord.com/) (web or desktop app)
2. Click the **"+"** button on the left sidebar → **Create My Own**
3. Choose **For me and my friends** (private server)
4. Name your server (e.g., "MJ API Relay")
5. Create a dedicated text channel for Midjourney (e.g., `#midjourney`)

### 3. Add the Midjourney Bot to Your Server

1. Go to [midjourney.com](https://www.midjourney.com/) and sign in
2. Open the [Midjourney Discord](https://discord.gg/midjourney) server
3. Find the **Midjourney Bot** in the member list, right-click → **Add to Server**
4. Select your server from the dropdown and authorize
5. Verify the bot appears in your server's member list

### 4. Create a Discord Bot (for Gateway Monitoring)

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** → name it (e.g., "MJ Relay Monitor")
3. Navigate to **Bot** tab → click **Reset Token** → **copy the token** → this is your `DISCORD_BOT_TOKEN`
4. Under **Privileged Gateway Intents**, enable:
   - ✅ **Message Content Intent**
   - ✅ **Server Members Intent** (optional)
5. Navigate to **OAuth2** → **URL Generator**:
   - Scopes: `bot`
   - Bot Permissions: `Read Messages/View Channels`, `Read Message History`
6. Copy the generated URL, open it, and **add the bot to your server**

### 5. Obtain Your Discord User Token

> ⚠️ **Important:** User tokens are used to send `/imagine` commands as your account. This is a self-bot technique — use at your own risk and in compliance with Discord's Terms of Service.

1. Open Discord in a **web browser** (not the desktop app)
2. Press `F12` to open Developer Tools
3. Go to the **Console** tab
4. Type the following and press Enter:
   ```js
   (webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()
   ```
5. Copy the output string (without quotes) → this is your `DISCORD_USER_TOKEN`

### 6. Get Your Channel ID

1. In Discord, go to **User Settings** → **Advanced** → enable **Developer Mode**
2. Right-click the Midjourney channel → **Copy Channel ID**
3. This is your `MJ_CHANNEL_ID`

### 7. System Requirements

- **Python** 3.12+
- **PostgreSQL** 16 (or Docker)
- **Docker & Docker Compose** (recommended for deployment)

## Getting Started

### Option A: Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/midjourney-api.git
cd midjourney-api

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your tokens and settings (see Configuration section)

# 3. Start everything
docker compose up -d

# 4. Verify
curl http://localhost:8000/health
# → {"status": "ok"}
```

### Option B: Local Development

```bash
# 1. Clone and set up virtual environment
git clone https://github.com/your-org/midjourney-api.git
cd midjourney-api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Start PostgreSQL via Docker
docker compose up -d db

# 5. Run database migrations
alembic upgrade head

# 6. Create an API key (see API Key Management below)

# 7. Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 8. Verify
curl http://localhost:8000/health
# → {"status": "ok"}
```

### API Key Management

API keys are stored as HMAC-SHA256 hashes. To create one:

```bash
# Generate a key hash (replace 'your-secret' with your API_KEY_SECRET from .env)
python -c "
import hmac, hashlib, secrets
raw_key = secrets.token_urlsafe(32)
secret = 'change-me-in-production'  # Must match API_KEY_SECRET in .env
key_hash = hmac.new(secret.encode(), raw_key.encode(), hashlib.sha256).hexdigest()
print(f'Raw API Key (use in X-API-Key header): {raw_key}')
print(f'Key Hash (store in database):          {key_hash}')
"
```

Then insert the hash into the database:

```sql
INSERT INTO api_keys (id, name, key_hash, daily_limit, monthly_limit, is_active)
VALUES (gen_random_uuid(), 'my-app', '<key_hash_from_above>', 50, 1000, true);
```

## API Reference

All endpoints except `/health` require the `X-API-Key` header.

### Health Check

```http
GET /health
```

```json
{ "status": "ok" }
```

### Submit Image Generation

```http
POST /api/v1/imagine
Content-Type: application/json
X-API-Key: your-api-key

{
  "prompt": "a cat astronaut floating in space, cinematic lighting",
  "aspect_ratio": "16:9",
  "upscale_count": 4
}
```

**Response** `202 Accepted`:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prompt` | string | *required* | The image generation prompt |
| `aspect_ratio` | string | `"1:1"` | Aspect ratio (`1:1`, `16:9`, `9:16`, `4:3`, etc.) |
| `upscale_count` | int | `1` | Number of images to auto-upscale (0–4) |

### Get Task Status

```http
GET /api/v1/tasks/{task_id}
X-API-Key: your-api-key
```

**Response** `200 OK`:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "prompt": "a cat astronaut floating in space, cinematic lighting",
  "aspect_ratio": "16:9",
  "status": "success",
  "progress": 100,
  "image_url": "https://cdn.discordapp.com/attachments/.../grid.png",
  "image_urls": [
    "https://cdn.discordapp.com/attachments/.../u1.png",
    "https://cdn.discordapp.com/attachments/.../u2.png",
    "https://cdn.discordapp.com/attachments/.../u3.png",
    "https://cdn.discordapp.com/attachments/.../u4.png"
  ],
  "created_at": "2026-02-22T10:30:00Z",
  "updated_at": "2026-02-22T10:31:45Z"
}
```

### List Tasks (Paginated)

```http
GET /api/v1/tasks?page=1&page_size=20
X-API-Key: your-api-key
```

### Check Quota

```http
GET /api/v1/quota
X-API-Key: your-api-key
```

**Response** `200 OK`:
```json
{
  "daily_limit": 50,
  "daily_used": 12,
  "daily_remaining": 38,
  "monthly_limit": 1000,
  "monthly_used": 156,
  "monthly_remaining": 844
}
```

### Usage Logs (Paginated)

```http
GET /api/v1/usage?page=1&start_date=2026-02-01&end_date=2026-02-28
X-API-Key: your-api-key
```

## How It Works

### Generation Workflow

```
  Client                      API Server                    Discord
    │                            │                             │
    │  POST /imagine             │                             │
    │  {prompt, aspect_ratio}    │                             │
    ├───────────────────────────►│                             │
    │                            │  1. Validate API key        │
    │                            │  2. Check quota             │
    │                            │  3. Create task (QUEUED)    │
    │  202 {task_id, status}     │  4. Enqueue for dispatch    │
    │◄───────────────────────────┤                             │
    │                            │                             │
    │                            │  5. Acquire semaphore slot  │
    │                            │  6. Task → PROCESSING       │
    │                            │                             │
    │                            │  /imagine prompt mjr-{tag}  │
    │                            ├────────────────────────────►│
    │                            │                             │
    │                            │  Progress: 25%... 50%...    │
    │                            │◄────────────────────────────┤
    │  GET /tasks/{id}           │                             │
    │  {progress: 50}            │  Grid complete!             │
    │◄──────────────────────────►│◄────────────────────────────┤
    │                            │                             │
    │                            │  7. Task → UPSCALING        │
    │                            │  8. Click U1, U2, U3, U4   │
    │                            ├────────────────────────────►│
    │                            │                             │
    │                            │  Upscale results            │
    │                            │◄────────────────────────────┤
    │                            │  9. Task → SUCCESS          │
    │                            │  10. Release semaphore      │
    │  GET /tasks/{id}           │                             │
    │  {status: success,         │                             │
    │   image_urls: [...]}       │                             │
    │◄──────────────────────────►│                             │
```

### Task State Machine

```
QUEUED ──► PROCESSING ──► UPSCALING ──► SUCCESS
                │                         │
                └────────► FAILED ◄───────┘
```

| State | Description |
|-------|-------------|
| `QUEUED` | Task created, waiting for semaphore slot |
| `PROCESSING` | `/imagine` command sent, waiting for grid |
| `UPSCALING` | Grid received, upscaling individual images |
| `SUCCESS` | All images ready, URLs stored |
| `FAILED` | Error occurred or timeout exceeded |

## Configuration

All configuration is via environment variables (loaded from `.env`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL async connection string |
| `DISCORD_BOT_TOKEN` | Yes | — | Bot token for Gateway monitoring |
| `DISCORD_USER_TOKEN` | Yes | — | User token for `/imagine` interactions |
| `MJ_CHANNEL_ID` | Yes | — | Discord channel ID for Midjourney |
| `MJ_MAX_CONCURRENT_JOBS` | No | `3` | Concurrent job limit (match your MJ plan) |
| `MJ_TASK_TIMEOUT_SECONDS` | No | `120` | Generation timeout (seconds) |
| `MJ_UPSCALE_TIMEOUT_SECONDS` | No | `180` | Upscale phase timeout (seconds) |
| `PLATFORM_DAILY_LIMIT` | No | `100` | Platform-wide daily limit |
| `API_KEY_SECRET` | No | `change-me-in-production` | HMAC secret for key hashing |
| `API_V1_PREFIX` | No | `/api/v1` | API version prefix |

## Testing

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_services.py

# Filter by test name
pytest -k "quota"
```

**Test Stack:** pytest + pytest-asyncio + aiosqlite (in-memory SQLite for isolation)

| Test File | Tests | Scope |
|-----------|-------|-------|
| `test_models.py` | 8 | ORM models, constraints, defaults |
| `test_auth.py` | 4 | API key validation |
| `test_protocol.py` | 6 | MidjourneyClient Protocol |
| `test_discord.py` | 21 | Message parser + correlation |
| `test_services.py` | 16 | Task, Quota, Usage services |
| `test_imagine.py` | 7 | ImagineService orchestration |
| `test_concurrency.py` | 8 | Dispatch loop + callbacks |
| `test_upscale.py` | 35 | Upscale workflow |
| `test_api.py` | 15 | Full endpoint integration |

### Code Quality

```bash
black src/ tests/        # Code formatting
isort src/ tests/        # Import sorting
ruff check src/ tests/   # Linting
mypy src/                # Type checking (strict mode)
```

## Project Structure

```
midjourney-api/
├── src/app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── imagine.py          # POST /imagine
│   │   │   ├── tasks.py            # GET /tasks
│   │   │   ├── quota.py            # GET /quota
│   │   │   ├── usage.py            # GET /usage
│   │   │   └── router.py           # Route aggregation
│   │   └── deps.py                 # Auth + DB dependencies
│   │
│   ├── core/
│   │   ├── concurrency.py          # Semaphore-based dispatch queue
│   │   ├── upscale_tracker.py      # In-memory upscale state
│   │   └── logging.py              # Structured JSON logging
│   │
│   ├── models/
│   │   ├── base.py                 # TaskStatus enum, TimestampMixin
│   │   ├── task.py                 # Task + UsageLog ORM models
│   │   └── api_key.py              # ApiKey + QuotaUsage models
│   │
│   ├── providers/
│   │   ├── protocol.py             # MidjourneyClient Protocol
│   │   ├── discord/
│   │   │   ├── client.py           # DiscordMidjourneyClient
│   │   │   ├── interaction.py      # Send /imagine via HTTP
│   │   │   ├── gateway.py          # WebSocket response monitor
│   │   │   ├── parser.py           # Parse MJ messages
│   │   │   └── correlation.py      # Tag ↔ task_id mapping
│   │   └── mock/
│   │       └── client.py           # MockMidjourneyClient
│   │
│   ├── schemas/                    # Pydantic v2 models
│   ├── services/                   # Business logic layer
│   ├── middleware/                  # Correlation ID middleware
│   ├── config.py                   # pydantic-settings
│   ├── database.py                 # Async engine + sessionmaker
│   └── main.py                     # App entry point + lifespan
│
├── alembic/                        # Database migrations
├── tests/
│   ├── unit/                       # Unit tests (85+)
│   ├── integration/                # API integration tests
│   └── conftest.py                 # Shared fixtures
│
├── docker-compose.yml              # PostgreSQL + API
├── Dockerfile                      # Multi-stage build
├── pyproject.toml                  # Dependencies + tool config
└── .env.example                    # Environment template
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API Framework** | FastAPI + Uvicorn | Async REST endpoints with auto-generated OpenAPI docs |
| **Database** | PostgreSQL 16 + SQLAlchemy 2.x | Async ORM with row-level locking for quota |
| **Migrations** | Alembic | Versioned schema management |
| **Discord Gateway** | discord.py | Real-time WebSocket monitoring for MJ responses |
| **Discord Interactions** | httpx | HTTP-based `/imagine` command dispatch |
| **Validation** | Pydantic v2 | Request/response schema validation |
| **Configuration** | pydantic-settings | Type-safe env var loading |
| **Testing** | pytest + pytest-asyncio | Async test suite with in-memory SQLite |
| **Containerization** | Docker + Compose | Multi-stage build, one-command deployment |
| **Code Quality** | black + isort + ruff + mypy | Formatting, linting, type checking |

## License

Private — All rights reserved.
