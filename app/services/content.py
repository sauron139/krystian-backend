"""Business logic shared by every content resource (projects, services, experience, skills,
posts). Each resource is described once by a `Resource`; routers and rules are generic."""

import re
import unicodedata
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_public_cache
from app.core.errors import AppError, conflict, not_found
from app.models import ContentMixin, Experience, Media, Post, Project, ServiceOffering, Skill
from app.models.enums import ContentStatus
from app.schemas import content as s


@dataclass(frozen=True)
class Resource:
    name: str  # URL segment, e.g. "projects"
    label: str  # human name for errors, e.g. "Project"
    model: type[ContentMixin]
    in_schema: type[BaseModel]
    patch_schema: type[BaseModel]
    out_schema: type[BaseModel]
    order_by: tuple[Any, ...]
    slug_from: str | None = None  # field to derive the slug from, if the resource has slugs
    media_fields: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_slug(self) -> bool:
        return self.slug_from is not None


PROJECTS = Resource(
    "projects", "Project", Project, s.ProjectIn, s.ProjectPatch, s.ProjectOut,
    order_by=(Project.featured.desc(), Project.sort_order, Project.published_at.desc()),
    slug_from="title", media_fields=("cover_id",),
)  # fmt: skip
SERVICES = Resource(
    "services", "Service", ServiceOffering, s.ServiceIn, s.ServicePatch, s.ServiceOut,
    order_by=(ServiceOffering.sort_order, ServiceOffering.created_at),
)  # fmt: skip
EXPERIENCE = Resource(
    "experience", "Experience entry", Experience, s.ExperienceIn, s.ExperiencePatch,
    s.ExperienceOut,
    order_by=(Experience.start_date.desc(), Experience.sort_order),
)  # fmt: skip
SKILLS = Resource(
    "skills", "Skill", Skill, s.SkillIn, s.SkillPatch, s.SkillOut,
    order_by=(Skill.sort_order, Skill.proficiency.desc(), Skill.name),
)  # fmt: skip
POSTS = Resource(
    "posts", "Post", Post, s.PostIn, s.PostPatch, s.PostOut,
    order_by=(Post.published_at.desc(), Post.created_at.desc()),
    slug_from="title", media_fields=("cover_id",),
)  # fmt: skip

RESOURCES = (PROJECTS, SERVICES, EXPERIENCE, SKILLS, POSTS)


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:100] or "item"


def to_columns(data: BaseModel, *, only_set: bool) -> dict[str, Any]:
    """Schema → column values. Nested models (e.g. links) become JSON-safe dicts; dates,
    UUIDs and enums stay as Python objects for the DB driver."""
    names = data.model_fields_set if only_set else type(data).model_fields.keys()
    out: dict[str, Any] = {}
    for name in names:
        value = getattr(data, name)
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json", exclude_none=True)
        out[name] = value
    return out


# ---------------- queries ----------------
def select_all(res: Resource) -> Select[Any]:
    return select(res.model)


def published_query(res: Resource) -> Select[Any]:
    return select(res.model).where(res.model.status == ContentStatus.PUBLISHED)


async def paginate(
    session: AsyncSession, query: Select[Any], order_by: Sequence[Any], page: int, page_size: int
) -> tuple[list[Any], int]:
    total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = await session.scalars(
        query.order_by(*order_by).offset((page - 1) * page_size).limit(page_size)
    )
    return list(rows), total or 0


async def get_item(session: AsyncSession, res: Resource, item_id: uuid.UUID) -> Any:
    obj = await session.get(res.model, item_id)
    if obj is None:
        raise not_found(res.label)
    return obj


async def get_published_by_slug(session: AsyncSession, res: Resource, slug: str) -> Any:
    obj = await session.scalar(published_query(res).where(res.model.slug == slug))  # type: ignore[attr-defined]
    if obj is None:
        raise not_found(res.label)
    return obj


# ---------------- writes ----------------
async def _unique_slug(session: AsyncSession, res: Resource, base: str, exclude: Any = None) -> str:
    slug, n = base, 2
    while True:
        q = select(res.model.id).where(res.model.slug == slug)  # type: ignore[attr-defined]
        if exclude is not None:
            q = q.where(res.model.id != exclude)
        if await session.scalar(q) is None:
            return slug
        slug, n = f"{base}-{n}", n + 1


async def _check_media(session: AsyncSession, res: Resource, values: dict[str, Any]) -> None:
    for f in res.media_fields:
        media_id = values.get(f)
        if media_id is not None and await session.get(Media, media_id) is None:
            raise AppError(422, "invalid_reference", f"{f} does not reference existing media")


def _stamp_publication(obj: Any) -> None:
    if (
        hasattr(obj, "published_at")
        and obj.status == ContentStatus.PUBLISHED
        and obj.published_at is None
    ):
        obj.published_at = datetime.now(UTC)


async def create_item(session: AsyncSession, res: Resource, data: BaseModel) -> Any:
    values = to_columns(data, only_set=False)
    await _check_media(session, res, values)
    if res.has_slug:
        values["slug"] = values.get("slug") or await _unique_slug(
            session, res, slugify(values[res.slug_from or ""])
        )
    obj = res.model(**values)
    _stamp_publication(obj)
    session.add(obj)
    await _commit(session, res)
    await session.refresh(obj)
    return obj


async def update_item(session: AsyncSession, res: Resource, obj: Any, data: BaseModel) -> Any:
    values = to_columns(data, only_set=True)
    await _check_media(session, res, values)
    # Editing a placeholder means it's now real content, unless the caller says otherwise.
    values.setdefault("is_placeholder", False)
    if values["is_placeholder"] is None:
        values["is_placeholder"] = False
    for key, value in values.items():
        if value is None and key in {"slug", "title", "summary", "body", "category", "name"}:
            continue  # required columns: an explicit null means "unchanged"
        setattr(obj, key, value)
    _stamp_publication(obj)
    await _commit(session, res)
    await session.refresh(obj)
    return obj


async def delete_item(session: AsyncSession, res: Resource, obj: Any) -> None:
    await session.delete(obj)
    await _commit(session, res)


async def reorder_items(session: AsyncSession, res: Resource, ids: list[uuid.UUID]) -> None:
    rows = {o.id: o for o in await session.scalars(select(res.model).where(res.model.id.in_(ids)))}
    missing = [str(i) for i in ids if i not in rows]
    if missing:
        raise AppError(422, "invalid_reference", "Unknown ids", {"ids": missing})
    for position, item_id in enumerate(ids):
        rows[item_id].sort_order = position
    await _commit(session, res)


async def _commit(session: AsyncSession, res: Resource) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise conflict(f"{res.label} conflicts with an existing one (duplicate slug?)") from exc
    await invalidate_public_cache()


def status_filter(res: Resource, status: ContentStatus | None) -> list[ColumnElement[bool]]:
    return [res.model.status == status] if status else []
