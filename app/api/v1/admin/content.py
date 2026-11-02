"""Admin CRUD, generated once per content resource from its `Resource` description.

FastAPI reads parameter annotations at runtime to build validation and the OpenAPI schema,
so annotating with `res.in_schema` gives each resource its own typed, documented endpoints.
mypy can't follow types held in variables, hence the `valid-type` ignores."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.deps import PageDep, SessionDep, current_admin
from app.models.enums import ContentStatus
from app.schemas.common import Page, ReorderIn
from app.services import content as svc


def crud_router(res: svc.Resource) -> APIRouter:
    router = APIRouter(
        prefix=f"/{res.name}",
        tags=[f"admin: {res.name}"],
        dependencies=[Depends(current_admin)],
    )
    In, Patch, Out = res.in_schema, res.patch_schema, res.out_schema

    @router.get("", response_model=Page[Out], name=f"admin_list_{res.name}")  # type: ignore[valid-type]
    async def list_items(
        session: SessionDep, pg: PageDep, status: ContentStatus | None = None
    ) -> Any:
        q = svc.select_all(res).where(*svc.status_filter(res, status))
        order = (res.model.sort_order, res.model.created_at.desc())
        rows, total = await svc.paginate(session, q, order, pg.page, pg.page_size)
        return {"items": rows, "total": total, "page": pg.page, "page_size": pg.page_size}

    @router.post(
        "", response_model=Out, status_code=status.HTTP_201_CREATED, name=f"admin_create_{res.name}"
    )
    async def create(data: In, session: SessionDep) -> Any:  # type: ignore[valid-type]
        return await svc.create_item(session, res, data)

    @router.post(
        "/reorder", status_code=status.HTTP_204_NO_CONTENT, name=f"admin_reorder_{res.name}"
    )
    async def reorder(data: ReorderIn, session: SessionDep) -> None:
        await svc.reorder_items(session, res, data.ids)

    @router.get("/{item_id}", response_model=Out, name=f"admin_get_{res.name}")
    async def get(item_id: uuid.UUID, session: SessionDep) -> Any:
        return await svc.get_item(session, res, item_id)

    @router.patch("/{item_id}", response_model=Out, name=f"admin_update_{res.name}")
    async def update(item_id: uuid.UUID, data: Patch, session: SessionDep) -> Any:  # type: ignore[valid-type]
        obj = await svc.get_item(session, res, item_id)
        return await svc.update_item(session, res, obj, data)

    @router.delete(
        "/{item_id}", status_code=status.HTTP_204_NO_CONTENT, name=f"admin_delete_{res.name}"
    )
    async def delete(item_id: uuid.UUID, session: SessionDep) -> None:
        obj = await svc.get_item(session, res, item_id)
        await svc.delete_item(session, res, obj)

    return router


def all_crud_routers() -> list[APIRouter]:
    return [crud_router(res) for res in svc.RESOURCES]
