<div align="center">

# 🎨 Midjourney Relay API

**透過簡潔的 REST API 實現 Midjourney 圖像程式化生成**

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

*提交 prompt，取回高解析度圖片 — 無需打開 Discord 客戶端。*

</div>

<br />

## 目錄

- [概述](#概述)
- [系統架構](#系統架構)
- [前置作業](#前置作業)
- [快速開始](#快速開始)
- [API 參考](#api-參考)
- [運作流程](#運作流程)
- [環境設定](#環境設定)
- [測試](#測試)
- [專案結構](#專案結構)
- [技術棧](#技術棧)
- [授權](#授權)

## 概述

Midjourney Relay API 在你的應用程式與 Midjourney 圖像生成能力之間建立橋樑。由於 Midjourney 完全透過 Discord 運作，本 API 自動化了整個互動流程 — 發送 `/imagine` 指令、追蹤生成進度、自動放大圖片，最後回傳高解析度圖片 URL — 全部透過簡潔的 REST 介面完成。

### 核心功能

- **RESTful API** — 透過標準 HTTP 提交 prompt 並輪詢結果
- **自動放大** — 自動放大生成的圖片（每個九宮格可放大 1–4 張）
- **並行控制** — 遵守 Midjourney 的並行作業限制（Standard: 3 / Pro: 12）
- **配額管理** — 每日、每月與平台級別的速率限制，使用原子操作確保一致性
- **多租戶** — API Key 認證機制，支援每個 Key 獨立的配額追蹤
- **全面非同步** — 整個技術棧基於 async/await 構建，最大化吞吐量
- **Provider 抽象** — 基於 Protocol 的設計，可替換 Discord 為未來的 Provider
- **關聯追蹤** — 在 prompt 中嵌入唯一標籤，可靠地匹配回應

## 系統架構

```
                         ┌─────────────────────────────────────────────┐
                         │            Midjourney Relay API             │
                         │                                             │
  用戶端應用              │  ┌─────────┐    ┌──────────┐               │
  ─────────────────►     │  │ FastAPI  │───►│  服務層   │               │
  POST /api/v1/imagine   │  │  路由    │    │ Services │               │
  X-API-Key: xxx         │  └────┬─────┘    └────┬─────┘               │
                         │       │               │                     │
                         │  ┌────▼─────┐    ┌────▼──────────────┐      │
                         │  │ API Key  │    │   並行控制器       │      │
                         │  │   認證   │    │ (Semaphore 佇列)  │      │
                         │  └──────────┘    └────┬──────────────┘      │
                         │                       │                     │
                         │            ┌──────────▼──────────┐          │
                         │            │   Discord Provider   │          │
                         │            │ ┌─────────────────┐ │          │
                         │            │ │InteractionClient│──────────────►  Discord API
                         │            │ │(發送 /imagine)   │ │          │   (Midjourney Bot)
                         │            │ └─────────────────┘ │          │
                         │            │ ┌─────────────────┐ │          │
                         │            │ │ GatewayMonitor  │◄──────────────  Discord Gateway
                         │            │ │(追蹤回應)       │ │          │    (WebSocket)
                         │            │ └─────────────────┘ │          │
                         │            └─────────────────────┘          │
                         │                       │                     │
                         │            ┌──────────▼──────────┐          │
                         │            │    PostgreSQL 16     │          │
                         │            │ 任務 · 配額 · 日誌   │          │
                         │            └─────────────────────┘          │
                         └─────────────────────────────────────────────┘
```

### 設計決策

| 決策 | 原因 |
|------|------|
| **Provider Protocol** | `MidjourneyClient` 介面將業務邏輯與 Discord 解耦；可用 `MockClient` 測試，未來可替換 Provider |
| **關聯標籤** | 在 prompt 中嵌入 `mjr-{uuid}` 以匹配 Midjourney 的非同步回應 |
| **Semaphore 佇列** | `asyncio.Semaphore` 確保不超過 Midjourney 的並行限制 |
| **原子配額** | PostgreSQL 行級鎖（`SELECT ... FOR UPDATE`）防止競態條件 |
| **全面非同步** | FastAPI + SQLAlchemy async + httpx — 整個堆疊零阻塞 I/O |

## 前置作業

開始設定 API 之前，你需要完成以下步驟：

### 1. 購買 Midjourney 訂閱方案

1. 前往 [midjourney.com](https://www.midjourney.com/)
2. 登入並選擇訂閱方案：
   - **Basic**（$10/月）— 約 200 次生成，3 個並行作業
   - **Standard**（$30/月）— 15 小時 Fast 模式，無限 Relax 模式，3 個並行作業
   - **Pro**（$60/月）— 30 小時 Fast 模式，無限 Relax 模式，**12 個並行作業**
   - **Mega**（$120/月）— 60 小時 Fast 模式，無限 Relax 模式，**12 個並行作業**

> **建議：** Standard 或 Pro 方案。`MJ_MAX_CONCURRENT_JOBS` 設定值應與你的方案並行限制一致。

### 2. 建立 Discord 伺服器

1. 開啟 [Discord](https://discord.com/)（網頁版或桌面應用程式）
2. 點擊左側欄的 **「+」** 按鈕 → **建立自己的伺服器**
3. 選擇 **自用，與朋友同樂**（私人伺服器）
4. 為伺服器命名（例如：「MJ API Relay」）
5. 建立一個專屬的文字頻道用於 Midjourney（例如：`#midjourney`）

### 3. 將 Midjourney Bot 加入你的伺服器

1. 前往 [midjourney.com](https://www.midjourney.com/) 並登入
2. 開啟 [Midjourney 官方 Discord 伺服器](https://discord.gg/midjourney)
3. 在成員列表中找到 **Midjourney Bot**，右鍵點擊 → **加到伺服器**
4. 從下拉選單中選擇你的伺服器並授權
5. 確認 Bot 已出現在你的伺服器成員列表中

### 4. 建立 Discord Bot（用於 Gateway 監控）

1. 前往 [Discord 開發者入口](https://discord.com/developers/applications)
2. 點擊 **New Application** → 命名（例如：「MJ Relay Monitor」）
3. 進入 **Bot** 頁籤 → 點擊 **Reset Token** → **複製 Token** → 這就是你的 `DISCORD_BOT_TOKEN`
4. 在 **Privileged Gateway Intents** 下，啟用：
   - ✅ **Message Content Intent**
   - ✅ **Server Members Intent**（可選）
5. 進入 **OAuth2** → **URL Generator**：
   - Scopes：`bot`
   - Bot Permissions：`Read Messages/View Channels`、`Read Message History`
6. 複製生成的 URL，打開它，然後**將 Bot 加入你的伺服器**

### 5. 取得你的 Discord User Token

> ⚠️ **重要提醒：** User Token 用於以你的帳號身分發送 `/imagine` 指令。這是一種 self-bot 技術 — 請自行評估風險，並確保符合 Discord 服務條款。

1. 用**瀏覽器**開啟 Discord（不是桌面應用程式）
2. 按 `F12` 開啟開發者工具
3. 切換到 **Console（主控台）** 頁籤
4. 輸入以下指令並按 Enter：
   ```js
   (webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()
   ```
5. 複製輸出的字串（不含引號）→ 這就是你的 `DISCORD_USER_TOKEN`

### 6. 取得頻道 ID

1. 在 Discord 中，前往 **使用者設定** → **進階** → 啟用**開發者模式**
2. 右鍵點擊 Midjourney 頻道 → **複製頻道 ID**
3. 這就是你的 `MJ_CHANNEL_ID`

### 7. 系統需求

- **Python** 3.12+
- **PostgreSQL** 16（或使用 Docker）
- **Docker & Docker Compose**（建議用於部署）

## 快速開始

### 方案 A：Docker（建議）

```bash
# 1. 克隆儲存庫
git clone https://github.com/your-org/midjourney-api.git
cd midjourney-api

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入你的 Token 和設定（參考「環境設定」章節）

# 3. 啟動所有服務
docker compose up -d

# 4. 驗證
curl http://localhost:8000/health
# → {"status": "ok"}
```

### 方案 B：本地開發

```bash
# 1. 克隆並建立虛擬環境
git clone https://github.com/your-org/midjourney-api.git
cd midjourney-api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 安裝依賴
pip install -e ".[dev]"

# 3. 設定環境變數
cp .env.example .env
# 編輯 .env 填入你的 Token 和設定

# 4. 透過 Docker 啟動 PostgreSQL
docker compose up -d db

# 5. 執行資料庫遷移
alembic upgrade head

# 6. 建立 API Key（參考下方「API Key 管理」）

# 7. 啟動開發伺服器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 8. 驗證
curl http://localhost:8000/health
# → {"status": "ok"}
```

### API Key 管理

API Key 使用 HMAC-SHA256 雜湊儲存。建立方式：

```bash
# 產生 Key 雜湊（將 'your-secret' 替換為 .env 中的 API_KEY_SECRET）
python -c "
import hmac, hashlib, secrets
raw_key = secrets.token_urlsafe(32)
secret = 'change-me-in-production'  # 必須與 .env 中的 API_KEY_SECRET 一致
key_hash = hmac.new(secret.encode(), raw_key.encode(), hashlib.sha256).hexdigest()
print(f'Raw API Key（用於 X-API-Key header）: {raw_key}')
print(f'Key Hash（存入資料庫）:              {key_hash}')
"
```

然後將雜湊值插入資料庫：

```sql
INSERT INTO api_keys (id, name, key_hash, daily_limit, monthly_limit, is_active)
VALUES (gen_random_uuid(), 'my-app', '<上面產生的_key_hash>', 50, 1000, true);
```

## API 參考

除了 `/health` 以外，所有端點都需要 `X-API-Key` 標頭。

### 健康檢查

```http
GET /health
```

```json
{ "status": "ok" }
```

### 提交圖像生成

```http
POST /api/v1/imagine
Content-Type: application/json
X-API-Key: your-api-key

{
  "prompt": "一隻太空人貓咪漂浮在宇宙中，電影級打光",
  "aspect_ratio": "16:9",
  "upscale_count": 4
}
```

**回應** `202 Accepted`：
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

| 欄位 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `prompt` | string | *必填* | 圖像生成的 prompt |
| `aspect_ratio` | string | `"1:1"` | 長寬比（`1:1`、`16:9`、`9:16`、`4:3` 等） |
| `upscale_count` | int | `1` | 自動放大的圖片數量（0–4） |

### 查詢任務狀態

```http
GET /api/v1/tasks/{task_id}
X-API-Key: your-api-key
```

**回應** `200 OK`：
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "prompt": "一隻太空人貓咪漂浮在宇宙中，電影級打光",
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

### 列出任務（分頁）

```http
GET /api/v1/tasks?page=1&page_size=20
X-API-Key: your-api-key
```

### 查詢配額

```http
GET /api/v1/quota
X-API-Key: your-api-key
```

**回應** `200 OK`：
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

### 使用紀錄（分頁）

```http
GET /api/v1/usage?page=1&start_date=2026-02-01&end_date=2026-02-28
X-API-Key: your-api-key
```

## 運作流程

### 圖像生成工作流程

```
  用戶端                     API 伺服器                    Discord
    │                            │                             │
    │  POST /imagine             │                             │
    │  {prompt, aspect_ratio}    │                             │
    ├───────────────────────────►│                             │
    │                            │  1. 驗證 API Key            │
    │                            │  2. 檢查配額                │
    │                            │  3. 建立任務（QUEUED）       │
    │  202 {task_id, status}     │  4. 排入派發佇列            │
    │◄───────────────────────────┤                             │
    │                            │                             │
    │                            │  5. 取得 Semaphore 位置     │
    │                            │  6. 任務 → PROCESSING       │
    │                            │                             │
    │                            │  /imagine prompt mjr-{tag}  │
    │                            ├────────────────────────────►│
    │                            │                             │
    │                            │  進度：25%... 50%...         │
    │                            │◄────────────────────────────┤
    │  GET /tasks/{id}           │                             │
    │  {progress: 50}            │  九宮格完成！               │
    │◄──────────────────────────►│◄────────────────────────────┤
    │                            │                             │
    │                            │  7. 任務 → UPSCALING        │
    │                            │  8. 點擊 U1, U2, U3, U4   │
    │                            ├────────────────────────────►│
    │                            │                             │
    │                            │  放大結果                   │
    │                            │◄────────────────────────────┤
    │                            │  9. 任務 → SUCCESS          │
    │                            │  10. 釋放 Semaphore         │
    │  GET /tasks/{id}           │                             │
    │  {status: success,         │                             │
    │   image_urls: [...]}       │                             │
    │◄──────────────────────────►│                             │
```

### 任務狀態機

```
QUEUED ──► PROCESSING ──► UPSCALING ──► SUCCESS
                │                         │
                └────────► FAILED ◄───────┘
```

| 狀態 | 說明 |
|------|------|
| `QUEUED` | 任務已建立，等待 Semaphore 可用位置 |
| `PROCESSING` | `/imagine` 指令已發送，等待九宮格圖片 |
| `UPSCALING` | 九宮格已收到，正在放大個別圖片 |
| `SUCCESS` | 所有圖片就緒，URL 已儲存 |
| `FAILED` | 發生錯誤或超過逾時時間 |

## 環境設定

所有設定透過環境變數管理（從 `.env` 檔案載入）：

| 變數 | 必填 | 預設值 | 說明 |
|------|------|--------|------|
| `DATABASE_URL` | 是 | — | PostgreSQL 非同步連線字串 |
| `DISCORD_BOT_TOKEN` | 是 | — | Bot Token，用於 Gateway 監控 |
| `DISCORD_USER_TOKEN` | 是 | — | User Token，用於 `/imagine` 互動 |
| `MJ_CHANNEL_ID` | 是 | — | Discord 頻道 ID（Midjourney 使用的頻道） |
| `MJ_MAX_CONCURRENT_JOBS` | 否 | `3` | 並行作業限制（應與 MJ 方案一致） |
| `MJ_TASK_TIMEOUT_SECONDS` | 否 | `120` | 生成逾時時間（秒） |
| `MJ_UPSCALE_TIMEOUT_SECONDS` | 否 | `180` | 放大階段逾時時間（秒） |
| `PLATFORM_DAILY_LIMIT` | 否 | `100` | 平台級每日限制 |
| `API_KEY_SECRET` | 否 | `change-me-in-production` | HMAC 金鑰雜湊用的密鑰 |
| `API_V1_PREFIX` | 否 | `/api/v1` | API 版本前綴 |

## 測試

```bash
# 執行所有測試
pytest

# 詳細輸出
pytest -v

# 僅執行單元測試
pytest tests/unit/

# 僅執行整合測試
pytest tests/integration/

# 特定測試檔案
pytest tests/unit/test_services.py

# 依名稱篩選
pytest -k "quota"
```

**測試技術棧：** pytest + pytest-asyncio + aiosqlite（記憶體內 SQLite 做隔離）

| 測試檔案 | 測試數 | 範圍 |
|----------|--------|------|
| `test_models.py` | 8 | ORM 模型、約束、預設值 |
| `test_auth.py` | 4 | API Key 驗證 |
| `test_protocol.py` | 6 | MidjourneyClient Protocol |
| `test_discord.py` | 21 | 訊息解析器 + 關聯管理 |
| `test_services.py` | 16 | Task、Quota、Usage 服務 |
| `test_imagine.py` | 7 | ImagineService 編排 |
| `test_concurrency.py` | 8 | 派發迴圈 + 回呼 |
| `test_upscale.py` | 35 | 放大工作流程 |
| `test_api.py` | 15 | 完整端點整合測試 |

### 程式碼品質

```bash
black src/ tests/        # 程式碼格式化
isort src/ tests/        # Import 排序
ruff check src/ tests/   # 程式碼檢查
mypy src/                # 型別檢查（嚴格模式）
```

## 專案結構

```
midjourney-api/
├── src/app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── imagine.py          # POST /imagine
│   │   │   ├── tasks.py            # GET /tasks
│   │   │   ├── quota.py            # GET /quota
│   │   │   ├── usage.py            # GET /usage
│   │   │   └── router.py           # 路由聚合
│   │   └── deps.py                 # 認證 + DB 依賴注入
│   │
│   ├── core/
│   │   ├── concurrency.py          # Semaphore 派發佇列
│   │   ├── upscale_tracker.py      # 記憶體內放大狀態
│   │   └── logging.py              # 結構化 JSON 日誌
│   │
│   ├── models/
│   │   ├── base.py                 # TaskStatus 列舉、TimestampMixin
│   │   ├── task.py                 # Task + UsageLog ORM 模型
│   │   └── api_key.py              # ApiKey + QuotaUsage 模型
│   │
│   ├── providers/
│   │   ├── protocol.py             # MidjourneyClient Protocol
│   │   ├── discord/
│   │   │   ├── client.py           # DiscordMidjourneyClient
│   │   │   ├── interaction.py      # 透過 HTTP 發送 /imagine
│   │   │   ├── gateway.py          # WebSocket 回應監控
│   │   │   ├── parser.py           # 解析 MJ 訊息
│   │   │   └── correlation.py      # 標籤 ↔ task_id 映射
│   │   └── mock/
│   │       └── client.py           # MockMidjourneyClient
│   │
│   ├── schemas/                    # Pydantic v2 模型
│   ├── services/                   # 業務邏輯層
│   ├── middleware/                  # Correlation ID 中介軟體
│   ├── config.py                   # pydantic-settings
│   ├── database.py                 # 非同步引擎 + sessionmaker
│   └── main.py                     # 應用程式入口 + lifespan
│
├── alembic/                        # 資料庫遷移
├── tests/
│   ├── unit/                       # 單元測試（120+）
│   ├── integration/                # API 整合測試
│   └── conftest.py                 # 共用 Fixtures
│
├── docker-compose.yml              # PostgreSQL + API
├── Dockerfile                      # 多階段建置
├── pyproject.toml                  # 依賴 + 工具設定
└── .env.example                    # 環境變數範本
```

## 技術棧

| 層級 | 技術 | 用途 |
|------|------|------|
| **API 框架** | FastAPI + Uvicorn | 非同步 REST 端點，自動生成 OpenAPI 文件 |
| **資料庫** | PostgreSQL 16 + SQLAlchemy 2.x | 非同步 ORM，行級鎖用於配額管理 |
| **遷移** | Alembic | 版本化的 Schema 管理 |
| **Discord Gateway** | discord.py | 即時 WebSocket 監控 MJ 回應 |
| **Discord 互動** | httpx | 基於 HTTP 的 `/imagine` 指令派發 |
| **驗證** | Pydantic v2 | 請求/回應 Schema 驗證 |
| **設定** | pydantic-settings | 型別安全的環境變數載入 |
| **測試** | pytest + pytest-asyncio | 非同步測試套件，使用記憶體內 SQLite |
| **容器化** | Docker + Compose | 多階段建置，一行指令部署 |
| **程式碼品質** | black + isort + ruff + mypy | 格式化、檢查、型別檢查 |

## 授權

Private — 保留所有權利。
