import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import PageDep, SessionDep, current_admin
from app.core.errors import not_found
from app.models import ContactMessage, Profile, SiteSettings
from app.models.enums import MessageStatus
from app.schemas.common import Page
from app.schemas.inbox import MessageOut, MessagePatch
from app.schemas.site import (
    ContentChecklist,
    ProfileIn,
    ProfileOut,
    SiteSettingsIn,
    SiteSettingsOut,
)
from app.services import content as svc
from app.services import site as site_service

router = APIRouter(dependencies=[Depends(current_admin)])


@router.get("/profile", response_model=ProfileOut, tags=["admin: profile"])
async def get_profile(session: SessionDep) -> Profile:
    return await site_service.get_profile(session)


@router.put("/profile", response_model=ProfileOut, tags=["admin: profile"])
async def put_profile(data: ProfileIn, session: SessionDep) -> Profile:
    return await site_service.update_profile(session, data)


@router.get("/site-settings", response_model=SiteSettingsOut, tags=["admin: site settings"])
async def get_site_settings(session: SessionDep) -> SiteSettings:
    return await site_service.get_site_settings(session)


@router.put("/site-settings", response_model=SiteSettingsOut, tags=["admin: site settings"])
async def put_site_settings(data: SiteSettingsIn, session: SessionDep) -> SiteSettings:
    return await site_service.update_site_settings(session, data)


@router.get("/content-checklist", response_model=ContentChecklist, tags=["admin: dashboard"])
async def content_checklist(session: SessionDep) -> ContentChecklist:
    return await site_service.content_checklist(session)


@router.get("/messages", response_model=Page[MessageOut], tags=["admin: messages"])
async def list_messages(
    session: SessionDep, pg: PageDep, status: MessageStatus | None = None
) -> Any:
    q = select(ContactMessage)
    if status:
        q = q.where(ContactMessage.status == status)
    rows, total = await svc.paginate(
        session, q, (ContactMessage.created_at.desc(),), pg.page, pg.page_size
    )
    return {"items": rows, "total": total, "page": pg.page, "page_size": pg.page_size}


@router.get("/messages/{message_id}", response_model=MessageOut, tags=["admin: messages"])
async def get_message(message_id: uuid.UUID, session: SessionDep) -> ContactMessage:
    msg = await session.get(ContactMessage, message_id)
    if msg is None:
        raise not_found("Message")
    return msg


@router.patch("/messages/{message_id}", response_model=MessageOut, tags=["admin: messages"])
async def update_message(
    message_id: uuid.UUID, data: MessagePatch, session: SessionDep
) -> ContactMessage:
    msg = await get_message(message_id, session)
    msg.status = data.status
    await session.commit()
    await session.refresh(msg)
    return msg
