# Endpoints: api

<!-- prospec:auto-start -->

## POST /api/v1/imagine

Submit an image generation task.

| Field | Value |
|-------|-------|
| **Method** | POST |
| **Path** | `/api/v1/imagine` |
| **Status** | 202 Accepted |
| **Auth** | `X-API-Key` header (required) |
| **Tags** | imagine |

**Request Body**:
```json
{
  "prompt": "a sunset over mountains",
  "aspect_ratio": "16:9"
}
```
- `prompt`: string, 1-4000 chars (required)
- `aspect_ratio`: string, regex `^\d+:\d+$`, default `"1:1"`

**Response**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

**Error Responses**: 400 (invalid prompt), 401 (invalid API key), 429 (quota exceeded)

---

## GET /api/v1/tasks/{task_id}

Get a specific task's status and result.

| Field | Value |
|-------|-------|
| **Method** | GET |
| **Path** | `/api/v1/tasks/{task_id}` |
| **Status** | 200 OK |
| **Auth** | `X-API-Key` header (required) |
| **Tags** | tasks |

**Path Params**: `task_id` (UUID)

**Response**:
```json
{
  "id": "550e8400-...",
  "prompt": "a sunset over mountains",
  "aspect_ratio": "16:9",
  "status": "success",
  "progress": 100,
  "image_url": "https://cdn.discordapp.com/...",
  "error_message": null,
  "created_at": "2026-02-22T12:00:00Z",
  "updated_at": "2026-02-22T12:01:30Z"
}
```

**Error Responses**: 401 (invalid API key), 404 (task not found or not owned)

---

## GET /api/v1/tasks

List tasks for the authenticated API key.

| Field | Value |
|-------|-------|
| **Method** | GET |
| **Path** | `/api/v1/tasks` |
| **Status** | 200 OK |
| **Auth** | `X-API-Key` header (required) |
| **Tags** | tasks |

**Query Params**:
- `page`: int, >= 1, default 1
- `page_size`: int, 1-100, default 20

**Response**:
```json
{
  "items": [{ "id": "...", "prompt": "...", ... }],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

## GET /api/v1/quota

Get remaining quota for the authenticated API key.

| Field | Value |
|-------|-------|
| **Method** | GET |
| **Path** | `/api/v1/quota` |
| **Status** | 200 OK |
| **Auth** | `X-API-Key` header (required) |
| **Tags** | quota |

**Response**:
```json
{
  "daily_remaining": 45,
  "daily_limit": 50,
  "monthly_remaining": 980,
  "monthly_limit": 1000,
  "platform_daily_remaining": 95
}
```

---

## GET /api/v1/usage

Get usage history for the authenticated API key.

| Field | Value |
|-------|-------|
| **Method** | GET |
| **Path** | `/api/v1/usage` |
| **Status** | 200 OK |
| **Auth** | `X-API-Key` header (required) |
| **Tags** | usage |

**Query Params**:
- `page`: int, >= 1, default 1
- `page_size`: int, 1-100, default 20
- `start_date`: date (optional, inclusive)
- `end_date`: date (optional, inclusive)

**Response**:
```json
{
  "items": [{
    "id": "...",
    "task_id": "...",
    "prompt": "a sunset over mountains",
    "aspect_ratio": "16:9",
    "status": "success",
    "image_url": "https://cdn.discordapp.com/...",
    "duration_seconds": 45.2,
    "created_at": "2026-02-22T12:01:30Z"
  }],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

---

## GET /health

Liveness check (no auth required).

| Field | Value |
|-------|-------|
| **Method** | GET |
| **Path** | `/health` |
| **Status** | 200 OK |
| **Auth** | None |

**Response**:
```json
{ "status": "ok" }
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
