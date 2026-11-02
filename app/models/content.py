"""Content shown on the public site. Every content model shares status / ordering /
placeholder fields via ContentMixin, which lets the admin CRUD code treat them uniformly."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk, str_enum
from app.models.enums import (
    Availability,
    ContentStatus,
    ExperienceType,
    ProjectCategory,
    SkillCategory,
)
from app.models.media import Media


class ContentMixin(UUIDPk, Timestamps):
    status: Mapped[ContentStatus] = mapped_column(
        str_enum(ContentStatus, "content_status"), default=ContentStatus.DRAFT, index=True
    )
    sort_order: Mapped[int] = mapped_column(default=0)
    # True for seed/placeholder content; cleared automatically when Krystian edits the item.
    is_placeholder: Mapped[bool] = mapped_column(default=False)


class Project(ContentMixin, Base):
    __tablename__ = "projects"

    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(400))
    body: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[ProjectCategory] = mapped_column(str_enum(ProjectCategory, "project_category"))
    tags: Mapped[list[str]] = mapped_column(default=list)
    tech_stack: Mapped[list[str]] = mapped_column(default=list)
    links: Mapped[dict[str, str]] = mapped_column(default=dict)
    featured: Mapped[bool] = mapped_column(default=False)
    published_at: Mapped[datetime | None]
    cover_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("media.id", ondelete="SET NULL"))
    cover: Mapped[Media | None] = relationship(lazy="selectin")


class ServiceOffering(ContentMixin, Base):
    """A freelance service ("Mission services"). Named ServiceOffering to avoid confusion
    with the app's service layer; the API resource is still `services`."""

    __tablename__ = "services"

    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(400))
    description: Mapped[str] = mapped_column(Text, default="")
    deliverables: Mapped[list[str]] = mapped_column(default=list)
    pricing_note: Mapped[str] = mapped_column(String(200), default="")


class Experience(ContentMixin, Base):
    __tablename__ = "experience"

    type: Mapped[ExperienceType] = mapped_column(str_enum(ExperienceType, "experience_type"))
    organization: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(200), default="")
    start_date: Mapped[date]
    end_date: Mapped[date | None]
    bullets: Mapped[list[str]] = mapped_column(default=list)


class Skill(ContentMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (CheckConstraint("proficiency BETWEEN 1 AND 5", name="proficiency_range"),)

    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[SkillCategory] = mapped_column(str_enum(SkillCategory, "skill_category"))
    years: Mapped[float] = mapped_column(default=0)
    proficiency: Mapped[int] = mapped_column(default=3)
    featured: Mapped[bool] = mapped_column(default=False)


class Post(ContentMixin, Base):
    __tablename__ = "posts"

    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(400))
    body: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[str]] = mapped_column(default=list)
    published_at: Mapped[datetime | None]
    cover_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("media.id", ondelete="SET NULL"))
    cover: Mapped[Media | None] = relationship(lazy="selectin")


class Profile(Base):
    """Singleton row (id is always 1)."""

    __tablename__ = "profile"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    full_name: Mapped[str] = mapped_column(String(120))
    headline: Mapped[str] = mapped_column(String(200))
    short_bio: Mapped[str] = mapped_column(String(600))
    long_bio: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(254), default="")
    socials: Mapped[dict[str, str]] = mapped_column(default=dict)
    availability: Mapped[Availability] = mapped_column(
        str_enum(Availability, "availability"), default=Availability.OPEN_TO_BOTH
    )
    is_placeholder: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    photo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("media.id", ondelete="SET NULL"))
    cv_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("media.id", ondelete="SET NULL"))
    photo: Mapped[Media | None] = relationship(foreign_keys=[photo_id], lazy="selectin")
    cv: Mapped[Media | None] = relationship(foreign_keys=[cv_id], lazy="selectin")


class SiteSettings(Base):
    """Singleton row (id is always 1)."""

    __tablename__ = "site_settings"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    seo_title: Mapped[str] = mapped_column(String(120))
    seo_description: Mapped[str] = mapped_column(String(300))
    show_blog: Mapped[bool] = mapped_column(default=False)
    show_cv_button: Mapped[bool] = mapped_column(default=False)
    is_placeholder: Mapped[bool] = mapped_column(default=False)
    extra: Mapped[dict[str, Any]] = mapped_column(default=dict)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    og_image_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media.id", ondelete="SET NULL")
    )
    og_image: Mapped[Media | None] = relationship(lazy="selectin")
