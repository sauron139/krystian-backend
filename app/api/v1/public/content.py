"""Public, read-only content API. Only published items; responses cached in Redis."""

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Query, status
from pydantic import TypeAdapter

from app.api.deps import ClientIP, PageDep, SessionDep
from app.core.cache import cached
from app.models import Project
from app.models.enums import ProjectCategory
from app.schemas.common import Page
from app.schemas.content import ExperienceOut, PostOut, ProjectOut, ServiceOut, SkillOut
from app.schemas.inbox import ContactAccepted, ContactIn
from app.schemas.site import ProfileOut, SiteSettingsOut
from app.services import contact as contact_service
from app.services import content as svc
from app.services import site as site_service

router = APIRouter(tags=["public"])


def _dump(schema: Any, obj: Any) -> Any:
    return TypeAdapter(schema).dump_python(TypeAdapter(schema).validate_python(obj), mode="json")


@router.get("/profile", response_model=ProfileOut)
async def get_profile(session: SessionDep) -> Any:
    async def load() -> Any:
        return _dump(ProfileOut, await site_service.get_profile(session))

    return await cached("profile", load)


@router.get("/site-settings", response_model=SiteSettingsOut)
async def get_site_settings(session: SessionDep) -> Any:
    async def load() -> Any:
        return _dump(SiteSettingsOut, await site_service.get_site_settings(session))

    return await cached("site-settings", load)


@router.get("/projects", response_model=Page[ProjectOut])
async def list_projects(
    session: SessionDep,
    pg: PageDep,
    category: ProjectCategory | None = None,
    tag: Annotated[str | None, Query(max_length=40)] = None,
    featured: bool | None = None,
) -> Any:
    async def load() -> Any:
        q = svc.published_query(svc.PROJECTS)
        if category:
            q = q.where(Project.category == category)
        if tag:
            q = q.where(Project.tags.contains([tag]))  # tags @> ARRAY[tag]
        if featured is not None:
            q = q.where(Project.featured.is_(featured))
        rows, total = await svc.paginate(session, q, svc.PROJECTS.order_by, pg.page, pg.page_size)
        return _dump(
            Page[ProjectOut],
            {"items": rows, "total": total, "page": pg.page, "page_size": pg.page_size},
        )

    key = f"projects:{category}:{tag}:{featured}:{pg.page}:{pg.page_size}"
    return await cached(key, load)


@router.get("/projects/{slug}", response_model=ProjectOut)
async def get_project(slug: str, session: SessionDep) -> Any:
    async def load() -> Any:
        return _dump(ProjectOut, await svc.get_published_by_slug(session, svc.PROJECTS, slug))

    return await cached(f"project:{slug}", load)


def _list_all(res: svc.Resource, out: Any) -> Any:
    """Small collections (services, experience, skills) are returned whole, not paginated."""

    async def endpoint(session: SessionDep) -> Any:
        async def load() -> Any:
            rows = await session.scalars(svc.published_query(res).order_by(*res.order_by))
            return _dump(list[out], list(rows))

        return await cached(res.name, load)

    return endpoint


router.add_api_route(
    "/services", _list_all(svc.SERVICES, ServiceOut), response_model=list[ServiceOut],
    name="list_services",
)  # fmt: skip
router.add_api_route(
    "/experience", _list_all(svc.EXPERIENCE, ExperienceOut), response_model=list[ExperienceOut],
    name="list_experience",
)  # fmt: skip
router.add_api_route(
    "/skills", _list_all(svc.SKILLS, SkillOut), response_model=list[SkillOut], name="list_skills"
)


@router.get("/posts", response_model=Page[PostOut])
async def list_posts(session: SessionDep, pg: PageDep) -> Any:
    async def load() -> Any:
        q = svc.published_query(svc.POSTS)
        rows, total = await svc.paginate(session, q, svc.POSTS.order_by, pg.page, pg.page_size)
        return _dump(
            Page[PostOut],
            {"items": rows, "total": total, "page": pg.page, "page_size": pg.page_size},
        )

    return await cached(f"posts:{pg.page}:{pg.page_size}", load)


@router.get("/posts/{slug}", response_model=PostOut)
async def get_post(slug: str, session: SessionDep) -> Any:
    async def load() -> Any:
        return _dump(PostOut, await svc.get_published_by_slug(session, svc.POSTS, slug))

    return await cached(f"post:{slug}", load)


@router.post("/contact", response_model=ContactAccepted, status_code=status.HTTP_202_ACCEPTED)
async def contact(
    data: ContactIn, session: SessionDep, ip: ClientIP, background: BackgroundTasks
) -> ContactAccepted:
    msg = await contact_service.receive_message(session, data, ip)
    if msg is not None:
        # Email after responding; the lead is already safely stored in the database.
        background.add_task(
            contact_service.notify_new_message,
            str(msg.id), msg.name, msg.email, msg.intent.value, msg.message,
        )  # fmt: skip
    return ContactAccepted()
