import hashlib
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.api_key import ApiKey


@pytest.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db(engine) -> AsyncSession:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
def raw_api_key() -> str:
    return f"test-key-{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def api_key(db: AsyncSession, raw_api_key: str) -> ApiKey:
    key_hash = hashlib.sha256(raw_api_key.encode()).hexdigest()
    key = ApiKey(
        name="Test Key",
        key_hash=key_hash,
        daily_limit=50,
        monthly_limit=1000,
        is_active=True,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key
