import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.admin import auth as admin_auth
from app.api.v1.admin import content as admin_content
from app.api.v1.admin import site as admin_site
from app.api.v1.public import content as public_content
from app.api.v1.public import health
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.redis import redis_client
from app.db.session import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    # Close pooled connections cleanly on shutdown.
    await engine.dispose()
    await redis_client.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Krystian API",
        version="0.2.0",
        lifespan=lifespan,
        # Hide interactive docs in production; the OpenAPI JSON stays available for codegen.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,  # needed for the refresh-token cookie
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    v1 = APIRouter(prefix="/v1")
    v1.include_router(health.router)
    v1.include_router(public_content.router)

    admin = APIRouter(prefix="/admin")
    admin.include_router(admin_auth.router)
    admin.include_router(admin_site.router)
    for router in admin_content.all_crud_routers():
        admin.include_router(router)
    v1.include_router(admin)

    app.include_router(v1)
    return app


app = create_app()
