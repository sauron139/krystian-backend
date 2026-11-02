import asyncio
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from app.core.redis import redis_client
from app.db.session import engine

router = APIRouter(tags=["health"])

CheckStatus = Literal["ok", "error"]


class HealthResponse(BaseModel):
    status: CheckStatus
    database: CheckStatus
    redis: CheckStatus


async def _check_database() -> CheckStatus:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


async def _check_redis() -> CheckStatus:
    try:
        await redis_client.ping()
        return "ok"
    except Exception:
        return "error"


@router.get("/health", response_model=HealthResponse)
async def health(response: Response) -> HealthResponse:
    """Liveness + dependency check. Returns 503 if Postgres or Redis is unreachable."""
    database, redis = await asyncio.gather(_check_database(), _check_redis())
    overall: CheckStatus = "ok" if database == redis == "ok" else "error"
    if overall == "error":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status=overall, database=database, redis=redis)
