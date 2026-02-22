# Midjourney Relay API

REST API that programmatically triggers Midjourney image generation via Discord and exposes task tracking, quota management, and usage logging.

## Architecture

```
Client ──▶ FastAPI (/api/v1) ──▶ Services ──▶ Discord Provider ──▶ Midjourney Bot
                │                    │              │
                │                    ▼              ├─ InteractionClient (send /imagine)
                │               PostgreSQL          └─ GatewayMonitor (track progress)
                │
                └─ API Key Auth (SHA-256)
```

**Key design decisions:**

- **Provider Abstraction** — `MidjourneyClient` Protocol enables swapping Discord automation for third-party providers
- **Correlation Tags** — Embeds `mjr-{uuid[:8]}` in prompts to match Midjourney responses back to tasks
- **Concurrency Control** — `asyncio.Semaphore` enforces Midjourney's concurrent job limit (Standard=3, Pro=12)
- **Atomic Quota** — Row-level locking prevents race conditions on daily/monthly limits

## Project Structure

```
src/app/
├── api/v1/          # FastAPI route handlers
├── core/            # Concurrency limiter, structured logging
├── middleware/       # X-Correlation-ID middleware
├── models/          # SQLAlchemy 2.x async models
├── providers/
│   ├── protocol.py  # MidjourneyClient Protocol
│   ├── mock/        # Mock provider for testing
│   └── discord/     # Discord automation provider
├── schemas/         # Pydantic v2 request/response models
├── services/        # Business logic (Task, Quota, Usage, Imagine)
├── config.py        # pydantic-settings configuration
├── database.py      # async engine + sessionmaker
└── main.py          # FastAPI app with lifespan
```

## Prerequisites

- Python 3.12+
- PostgreSQL 16 (or Docker)
- Discord Bot Token (Gateway monitoring)
- Discord User Token (Interaction API)
- Midjourney Bot added to your Discord server

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url> && cd midjourney-api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/midjourney_api` |
| `DISCORD_BOT_TOKEN` | Bot token from Discord Developer Portal | `MTIz...` |
| `DISCORD_USER_TOKEN` | User token for Interaction API | `user_token_here` |
| `MJ_CHANNEL_ID` | Discord channel ID where MJ Bot operates | `123456789012345678` |
| `MJ_MAX_CONCURRENT_JOBS` | Midjourney concurrency limit | `3` (Standard) / `12` (Pro) |
| `MJ_TASK_TIMEOUT_SECONDS` | Seconds before marking stale tasks as failed | `120` |
| `PLATFORM_DAILY_LIMIT` | Platform-wide daily generation limit | `100` |

### 3. Run with Docker (recommended)

```bash
docker compose up -d
```

This starts PostgreSQL 16 + the API server on port 8000.

### 4. Run locally (development)

```bash
# Start PostgreSQL
docker compose up -d db

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## API Endpoints

All endpoints (except `/health`) require the `X-API-Key` header.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/imagine` | Submit image generation request |
| `GET` | `/api/v1/tasks/{task_id}` | Get task status and result |
| `GET` | `/api/v1/tasks?page=1&page_size=20` | List tasks (paginated) |
| `GET` | `/api/v1/quota` | Get remaining quota |
| `GET` | `/api/v1/usage?start_date=2026-01-01&end_date=2026-01-31` | Usage logs (paginated) |

### Example: Generate an image

```bash
# Submit
curl -X POST http://localhost:8000/api/v1/imagine \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cat in space", "aspect_ratio": "16:9"}'

# Response: {"task_id": "uuid-here", "status": "queued"}

# Poll for result
curl http://localhost:8000/api/v1/tasks/<task_id> \
  -H "X-API-Key: your-api-key"
```

### Task lifecycle

```
QUEUED → PROCESSING → SUCCESS
                    → FAILED (error or timeout)
```

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_services.py

# Run specific test class
pytest tests/unit/test_discord.py::TestCorrelationManager

# Run integration tests only
pytest tests/integration/

# Run unit tests only
pytest tests/unit/
```

Test stack: pytest + pytest-asyncio + aiosqlite (in-memory SQLite for isolation).

**Current coverage: 85 tests across 8 test files**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_models.py` | 8 | Model creation, constraints, defaults |
| `test_auth.py` | 4 | API Key validation (valid/invalid/missing/inactive) |
| `test_protocol.py` | 6 | MidjourneyClient Protocol + MockClient |
| `test_discord.py` | 21 | Message parser + Correlation manager |
| `test_services.py` | 16 | TaskService + QuotaService + UsageService |
| `test_imagine.py` | 7 | ImagineService orchestration |
| `test_concurrency.py` | 8 | Dispatch, callbacks, timeout detection |
| `test_api.py` | 15 | Integration: all endpoints + full lifecycle |

## Linting and Formatting

```bash
black src/ tests/        # Code formatting
isort src/ tests/        # Import sorting
ruff check src/ tests/   # Linting
mypy src/                # Type checking
```

## API Key Management

API keys are stored as SHA-256 hashes. To create one, insert directly into the database:

```sql
INSERT INTO api_keys (name, key_hash, daily_limit, monthly_limit)
VALUES ('my-app', encode(sha256('your-raw-key-here'), 'hex'), 50, 1000);
```

Then use `your-raw-key-here` as the `X-API-Key` header value.

## Tech Stack

- **Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL 16 + SQLAlchemy 2.x async + Alembic
- **Discord**: discord.py (Gateway) + httpx (Interaction API)
- **Validation**: Pydantic v2
- **Testing**: pytest + pytest-asyncio + aiosqlite
- **Container**: Docker multi-stage build (python:3.12-slim)

## License

Private — All rights reserved.
