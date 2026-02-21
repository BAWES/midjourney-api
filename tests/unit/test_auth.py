"""Tests for API Key authentication dependency."""

import hashlib
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session
from app.database import get_db
from app.main import app
from app.models.api_key import ApiKey
from app.models.base import Base


@pytest.fixture
async def auth_engine():
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
async def auth_session_factory(auth_engine):
    return async_sessionmaker(auth_engine, expire_on_commit=False)


@pytest.fixture
async def auth_db(auth_session_factory):
    async with auth_session_factory() as session:
        yield session


@pytest.fixture
async def auth_client(auth_session_factory, auth_db: AsyncSession) -> AsyncClient:
    async def override_get_db():
        async with auth_session_factory() as session:
            yield session

    # Override both get_db (used by get_current_api_key) and get_db_session
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_session] = override_get_db

    # Set up imagine dependencies to avoid NoneType errors
    import asyncio
    from app.api.v1.imagine import set_dependencies
    from app.providers.discord.correlation import CorrelationManager

    set_dependencies(asyncio.Queue(), CorrelationManager())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


class TestApiKeyAuth:
    async def test_valid_api_key(
        self, auth_db: AsyncSession, auth_client: AsyncClient
    ) -> None:
        raw_key = "valid-test-key-12345"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = ApiKey(name="Valid", key_hash=key_hash, is_active=True)
        auth_db.add(api_key)
        await auth_db.commit()

        resp = await auth_client.get(
            "/api/v1/tasks", headers={"X-API-Key": raw_key}
        )
        assert resp.status_code == 200

    async def test_invalid_api_key(self, auth_client: AsyncClient) -> None:
        resp = await auth_client.get(
            "/api/v1/tasks", headers={"X-API-Key": "bad-key-does-not-exist"}
        )
        assert resp.status_code == 401

    async def test_missing_api_key(self, auth_client: AsyncClient) -> None:
        resp = await auth_client.get("/api/v1/tasks")
        assert resp.status_code in (401, 403, 422)

    async def test_inactive_api_key(
        self, auth_db: AsyncSession, auth_client: AsyncClient
    ) -> None:
        raw_key = "inactive-test-key-12345"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = ApiKey(name="Inactive", key_hash=key_hash, is_active=False)
        auth_db.add(api_key)
        await auth_db.commit()

        resp = await auth_client.get(
            "/api/v1/tasks", headers={"X-API-Key": raw_key}
        )
        assert resp.status_code == 401
