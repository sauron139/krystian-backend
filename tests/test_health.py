from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.public import health as health_module
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health_ok(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def ok() -> str:
        return "ok"

    monkeypatch.setattr(health_module, "_check_database", ok)
    monkeypatch.setattr(health_module, "_check_redis", ok)

    resp = await client.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "ok", "redis": "ok"}


async def test_health_reports_failure(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def ok() -> str:
        return "ok"

    async def fail() -> str:
        return "error"

    monkeypatch.setattr(health_module, "_check_database", ok)
    monkeypatch.setattr(health_module, "_check_redis", fail)

    resp = await client.get("/v1/health")
    assert resp.status_code == 503
    assert resp.json()["redis"] == "error"
