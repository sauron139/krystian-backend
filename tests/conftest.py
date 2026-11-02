"""Tests run against real Postgres and Redis (the same engines as production), using a
separate `krystian_test` database and Redis DB 15. Point elsewhere with TEST_DATABASE_URL
and TEST_REDIS_URL (the Docker setup does this)."""

import os

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://krystian:krystian-dev-only@localhost:5432/krystian_test",
)
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ.pop("NOTIFY_EMAIL", None)
os.environ.pop("TURNSTILE_SECRET", None)

from collections.abc import AsyncIterator

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

import app.models
from app.core.redis import redis_client
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.services.auth import upsert_admin

ADMIN_EMAIL = "admin@test.dev"
ADMIN_PASSWORD = "correct-horse-battery"


async def _ensure_database() -> None:
    url = make_url(os.environ["DATABASE_URL"])
    conn = await asyncpg.connect(
        user=url.username, password=url.password, host=url.host, port=url.port, database="postgres"
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", url.database)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{url.database}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
async def _schema() -> AsyncIterator[None]:
    await _ensure_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    await redis_client.aclose()


@pytest.fixture(autouse=True)
async def _clean() -> AsyncIterator[None]:
    """Each test starts with empty tables and an empty Redis DB."""
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await redis_client.flushdb()
    yield


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        yield s


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def admin_headers(client: AsyncClient, session: AsyncSession) -> dict[str, str]:
    await upsert_admin(session, ADMIN_EMAIL, ADMIN_PASSWORD)
    resp = await client.post(
        "/v1/admin/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def seeded(session: AsyncSession) -> None:
    from app.seed import seed

    await seed(session)
