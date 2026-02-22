"""Integration tests for API endpoints using httpx AsyncClient."""

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_api_key, get_db_session, hash_api_key
from app.models.api_key import ApiKey
from app.models.base import Base, TaskStatus
from app.main import app
from app.providers.discord.correlation import CorrelationManager
from app.services.task_service import TaskService


# --- Fixtures ---


@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture
async def test_db(test_session_factory):
    async with test_session_factory() as session:
        yield session


@pytest.fixture
def raw_key() -> str:
    return f"test-key-{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def test_api_key(test_db: AsyncSession, raw_key: str) -> ApiKey:
    key_hash = hash_api_key(raw_key)
    key = ApiKey(
        name="Test Key",
        key_hash=key_hash,
        daily_limit=50,
        monthly_limit=1000,
        is_active=True,
    )
    test_db.add(key)
    await test_db.commit()
    await test_db.refresh(key)
    return key


@pytest.fixture
async def client(
    test_session_factory, test_db: AsyncSession, test_api_key: ApiKey, raw_key: str
) -> AsyncClient:
    # Override dependencies
    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    async def override_get_api_key():
        return test_api_key

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_current_api_key] = override_get_api_key

    # Set up imagine endpoint dependencies
    from app.api.v1.imagine import set_dependencies

    queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
    correlation = CorrelationManager()
    set_dependencies(queue, correlation)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def unauth_client() -> AsyncClient:
    # Client without dependency overrides — tests auth rejection
    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# --- Health Check ---


class TestHealthCheck:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# --- Auth ---


class TestAuth:
    async def test_missing_api_key_returns_401(self, unauth_client: AsyncClient) -> None:
        resp = await unauth_client.get("/api/v1/tasks")
        assert resp.status_code in (401, 403, 422)


# --- Tasks API ---


class TestTasksAPI:
    async def test_get_task_not_found(self, client: AsyncClient) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/tasks/{fake_id}")
        assert resp.status_code == 404

    async def test_list_tasks_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_imagine_and_get_task(
        self, client: AsyncClient, test_session_factory
    ) -> None:
        # Submit
        resp = await client.post(
            "/api/v1/imagine",
            json={"prompt": "a cat in space", "aspect_ratio": "16:9"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"
        task_id = data["task_id"]

        # Get the task
        resp = await client.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200
        task_data = resp.json()
        assert task_data["prompt"] == "a cat in space"
        assert task_data["aspect_ratio"] == "16:9"
        assert task_data["status"] == "queued"
        assert task_data["progress"] == 0

    async def test_list_tasks_after_imagine(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/imagine", json={"prompt": "prompt 1"}
        )
        await client.post(
            "/api/v1/imagine", json={"prompt": "prompt 2"}
        )
        resp = await client.get("/api/v1/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_tasks_pagination(self, client: AsyncClient) -> None:
        for i in range(5):
            await client.post(
                "/api/v1/imagine", json={"prompt": f"prompt {i}"}
            )
        resp = await client.get("/api/v1/tasks?page=1&page_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2


# --- Quota API ---


class TestQuotaAPI:
    async def test_get_quota(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/quota")
        assert resp.status_code == 200
        data = resp.json()
        assert "daily_remaining" in data
        assert "daily_limit" in data
        assert "monthly_remaining" in data
        assert "monthly_limit" in data
        assert "platform_daily_remaining" in data

    async def test_quota_decreases_after_imagine(self, client: AsyncClient) -> None:
        resp1 = await client.get("/api/v1/quota")
        initial = resp1.json()["daily_remaining"]

        await client.post(
            "/api/v1/imagine", json={"prompt": "test quota"}
        )

        resp2 = await client.get("/api/v1/quota")
        after = resp2.json()["daily_remaining"]
        assert after == initial - 1


# --- Usage API ---


class TestUsageAPI:
    async def test_list_usage_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0


# --- Imagine API ---


class TestImagineAPI:
    async def test_imagine_returns_202(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/imagine",
            json={"prompt": "a beautiful sunset"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "queued"

    async def test_imagine_invalid_body(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/imagine", json={})
        assert resp.status_code == 422

    async def test_imagine_invalid_aspect_ratio(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/imagine",
            json={"prompt": "test", "aspect_ratio": "invalid"},
        )
        assert resp.status_code == 422

    async def test_imagine_empty_prompt(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/imagine",
            json={"prompt": ""},
        )
        assert resp.status_code == 422


# --- Full Flow ---


class TestFullFlow:
    async def test_imagine_to_task_lifecycle(
        self, client: AsyncClient, test_session_factory
    ) -> None:
        # 1. Submit imagine
        resp = await client.post(
            "/api/v1/imagine",
            json={"prompt": "a cat on the moon", "aspect_ratio": "1:1"},
        )
        assert resp.status_code == 202
        task_id = resp.json()["task_id"]

        # 2. Verify task is QUEUED
        resp = await client.get(f"/api/v1/tasks/{task_id}")
        assert resp.json()["status"] == "queued"

        # 3. Simulate state transition (service-level, not via API)
        async with test_session_factory() as db:
            task_svc = TaskService(db)
            await task_svc.transition(uuid.UUID(task_id), TaskStatus.PROCESSING)
            await task_svc.update_progress(uuid.UUID(task_id), 50)

        # 4. Verify PROCESSING state
        resp = await client.get(f"/api/v1/tasks/{task_id}")
        data = resp.json()
        assert data["status"] == "processing"
        assert data["progress"] == 50

        # 5. Simulate completion
        async with test_session_factory() as db:
            task_svc = TaskService(db)
            await task_svc.update_image_url(uuid.UUID(task_id), "https://cdn.example.com/img.png")
            await task_svc.transition(uuid.UUID(task_id), TaskStatus.SUCCESS)

        # 6. Verify SUCCESS state
        resp = await client.get(f"/api/v1/tasks/{task_id}")
        data = resp.json()
        assert data["status"] == "success"
        assert data["progress"] == 50
        assert data["image_url"] == "https://cdn.example.com/img.png"
