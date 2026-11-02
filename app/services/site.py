from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_public_cache
from app.core.errors import AppError, not_found
from app.models import Media, Profile, Project, SiteSettings
from app.models.enums import ContentStatus
from app.schemas.site import ChecklistItem, ContentChecklist, ProfileIn, SiteSettingsIn
from app.services.content import RESOURCES, to_columns


async def get_profile(session: AsyncSession) -> Profile:
    profile = await session.get(Profile, 1)
    if profile is None:
        raise not_found("Profile")
    return profile


async def get_site_settings(session: AsyncSession) -> SiteSettings:
    settings = await session.get(SiteSettings, 1)
    if settings is None:
        raise not_found("Site settings")
    return settings


async def _check_media_ids(session: AsyncSession, values: dict[str, object]) -> None:
    for key in ("photo_id", "cv_id", "og_image_id"):
        media_id = values.get(key)
        if media_id is not None and await session.get(Media, media_id) is None:
            raise AppError(422, "invalid_reference", f"{key} does not reference existing media")


async def update_profile(session: AsyncSession, data: ProfileIn) -> Profile:
    values = to_columns(data, only_set=False)
    values["email"] = values["email"] or ""
    await _check_media_ids(session, values)
    profile = await session.get(Profile, 1) or Profile(id=1)
    for k, v in values.items():
        setattr(profile, k, v)
    profile.is_placeholder = False
    session.add(profile)
    await session.commit()
    await invalidate_public_cache()
    await session.refresh(profile)
    return profile


async def update_site_settings(session: AsyncSession, data: SiteSettingsIn) -> SiteSettings:
    values = to_columns(data, only_set=False)
    await _check_media_ids(session, values)
    settings = await session.get(SiteSettings, 1) or SiteSettings(id=1)
    for k, v in values.items():
        setattr(settings, k, v)
    settings.is_placeholder = False
    session.add(settings)
    await session.commit()
    await invalidate_public_cache()
    await session.refresh(settings)
    return settings


async def content_checklist(session: AsyncSession) -> ContentChecklist:
    profile = await session.get(Profile, 1)
    settings = await session.get(SiteSettings, 1)
    counts: dict[str, int] = {}
    for res in RESOURCES:
        counts[res.name] = (
            await session.scalar(
                select(func.count()).select_from(res.model).where(res.model.is_placeholder)
            )
            or 0
        )
    real_projects = (
        await session.scalar(
            select(func.count())
            .select_from(Project)
            .where(Project.status == ContentStatus.PUBLISHED, Project.is_placeholder.is_(False))
        )
        or 0
    )
    items = [
        ChecklistItem(key="profile_bio", label="Write your name, headline and bio",
                      done=bool(profile and not profile.is_placeholder)),
        ChecklistItem(key="profile_photo", label="Add a profile photo",
                      done=bool(profile and profile.photo_id)),
        ChecklistItem(key="profile_cv", label="Upload your CV",
                      done=bool(profile and profile.cv_id)),
        ChecklistItem(key="projects", label="Publish at least 3 real projects",
                      done=real_projects >= 3),
        ChecklistItem(key="services", label="Replace the example services",
                      done=counts["services"] == 0),
        ChecklistItem(key="experience", label="Replace the placeholder experience",
                      done=counts["experience"] == 0),
        ChecklistItem(key="skills", label="Replace the example skills", done=counts["skills"] == 0),
        ChecklistItem(key="seo", label="Set the SEO title and description",
                      done=bool(settings and not settings.is_placeholder)),
    ]  # fmt: skip
    done = sum(i.done for i in items)
    return ContentChecklist(
        items=items, completed=done, total=len(items), placeholder_counts=counts
    )
