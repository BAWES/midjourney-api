# Archive Summary: build-midjourney-relay-api

## Overview

| Field | Value |
|-------|-------|
| Change Name | `build-midjourney-relay-api` |
| Created | 2026-02-21 |
| Archived | 2026-02-22 |
| Status at Archive | tasks (verified via manual 5+1 audit) |
| Task Completion | 25/25 (100%) |
| Test Results | 85/85 passed |
| Quality Grade | A (Good) |

## What Changed

Built the complete Midjourney Relay API from scratch — a FastAPI service that programmatically triggers Midjourney image generation via Discord and exposes the results through a REST API.

### User Stories Delivered

| US | Title | Priority | Status |
|----|-------|----------|--------|
| US-1 | Submit image generation request | P1 | Delivered |
| US-2 | Query task status | P1 | Delivered |
| US-3 | Discord integration — trigger and monitor | P1 | Delivered |
| US-4 | Quota control | P2 | Delivered |
| US-5 | Usage logging | P2 | Delivered |
| US-6 | Docker deployment | P1 | Delivered |

### Requirements Implemented

| REQ ID | Description | Status |
|--------|-------------|--------|
| REQ-API-001 | POST /imagine endpoint | Implemented |
| REQ-API-002 | GET /tasks/{id} status query | Implemented |
| REQ-API-003 | GET /tasks paginated list | Implemented |
| REQ-API-004 | GET /quota query | Implemented |
| REQ-API-005 | GET /usage paginated logs | Implemented |
| REQ-API-006 | GET /health endpoint | Implemented |
| REQ-DISCORD-001 | Trigger MJ /imagine via Interaction API | Implemented |
| REQ-DISCORD-002 | Monitor MJ Bot via Gateway | Implemented |
| REQ-DISCORD-003 | Message correlation via embedded tags | Implemented |
| REQ-TASK-001 | Task lifecycle state machine | Implemented |
| REQ-TASK-002 | Concurrency control (semaphore) | Implemented |
| REQ-QUOTA-001 | Per-key quota enforcement | Implemented |
| REQ-QUOTA-002 | Platform-wide daily limit | Implemented |
| REQ-USAGE-001 | Usage log recording | Implemented |
| REQ-AUTH-001 | API Key authentication (HMAC-SHA256) | Implemented |
| REQ-DEPLOY-001 | Docker deployment | Implemented |
| REQ-OBSERVE-001 | Structured logging with Correlation ID | Implemented |

### Key Architectural Decisions

1. **MidjourneyClient Protocol** — Abstract interface enabling swap between Discord automation and third-party providers
2. **Correlation Tags** — `mjr-{16-hex}` embedded in prompts for matching MJ responses to internal tasks
3. **Semaphore-based Concurrency** — `asyncio.Semaphore` limits concurrent MJ jobs (default 3)
4. **Atomic Quota** — Row-level lock + advisory lock prevents TOCTOU race conditions
5. **HMAC-SHA256 API Keys** — Server-secret-keyed hashing instead of unsalted SHA-256

### Post-Implementation Fixes

After initial implementation, a comprehensive code review identified and fixed:
- **CRITICAL**: Semaphore double-release, quota TOCTOU race, silent exception swallowing
- **HIGH**: Deprecated `datetime.utcnow()`, untyped mj_client, prompt injection risk, low correlation tag entropy, unsalted API key hashing, missing error handler

## Modules Affected

| Module | Files |
|--------|-------|
| API endpoints | `src/app/api/v1/imagine.py`, `tasks.py`, `quota.py`, `usage.py`, `router.py` |
| API dependencies | `src/app/api/deps.py` |
| Models | `src/app/models/base.py`, `api_key.py`, `task.py` |
| Schemas | `src/app/schemas/task.py` |
| Services | `src/app/services/task_service.py`, `quota_service.py`, `usage_service.py`, `imagine_service.py` |
| Core | `src/app/core/concurrency.py`, `logging.py` |
| Providers | `src/app/providers/protocol.py`, `discord/client.py`, `discord/gateway.py`, `discord/interaction.py`, `discord/parser.py`, `discord/correlation.py`, `mock/client.py` |
| Middleware | `src/app/middleware/correlation_id.py` |
| Config | `src/app/config.py`, `src/app/database.py` |
| Deployment | `Dockerfile`, `docker-compose.yml`, `.env.example` |
| Tests | `tests/conftest.py`, `tests/unit/`, `tests/integration/` |

## Artifacts

| Artifact | Path |
|----------|------|
| Proposal | `proposal.md` |
| Plan | `plan.md` |
| Delta Spec | `delta-spec.md` |
| Tasks | `tasks.md` |
| Metadata | `metadata.yaml` |

## Open Items Deferred

- Discord CDN URL expiration — images not persisted to own storage (accepted risk for MVP)
- Upscale/Variation support — deferred to `add-auto-upscale` story
- Webhook callback notifications — MVP uses polling via GET /tasks/{id}
