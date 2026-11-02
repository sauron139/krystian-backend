"""Schemas for content resources. Per resource: `XIn` (create), `XPatch` (partial update,
every field optional) and `XOut` (response, shared by public and admin endpoints)."""

import uuid
from datetime import date, datetime
from typing import Annotated, Self

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.models.enums import ContentStatus, ExperienceType, ProjectCategory, SkillCategory
from app.schemas.common import MediaOut, ORMModel, ShortText, Slug, Tag

Proficiency = Annotated[int, Field(ge=1, le=5)]
Years = Annotated[float, Field(ge=0, le=60)]


class ContentFields(BaseModel):
    status: ContentStatus = ContentStatus.DRAFT
    sort_order: int = 0


class ContentPatchFields(BaseModel):
    status: ContentStatus | None = None
    sort_order: int | None = None
    is_placeholder: bool | None = None


class ContentOutFields(ORMModel):
    id: uuid.UUID
    status: ContentStatus
    sort_order: int
    is_placeholder: bool
    created_at: datetime
    updated_at: datetime


# ---------- Project ----------
class ProjectLinks(BaseModel):
    repo: HttpUrl | None = None
    demo: HttpUrl | None = None
    paper: HttpUrl | None = None


class ProjectIn(ContentFields):
    slug: Slug | None = Field(default=None, description="Generated from the title if omitted")
    title: ShortText = Field(min_length=1)
    summary: str = Field(min_length=1, max_length=400)
    body: str = ""
    category: ProjectCategory
    tags: list[Tag] = []
    tech_stack: list[Tag] = []
    links: ProjectLinks = ProjectLinks()
    featured: bool = False
    cover_id: uuid.UUID | None = None


class ProjectPatch(ContentPatchFields):
    slug: Slug | None = None
    title: ShortText | None = Field(default=None, min_length=1)
    summary: str | None = Field(default=None, min_length=1, max_length=400)
    body: str | None = None
    category: ProjectCategory | None = None
    tags: list[Tag] | None = None
    tech_stack: list[Tag] | None = None
    links: ProjectLinks | None = None
    featured: bool | None = None
    cover_id: uuid.UUID | None = None


class ProjectOut(ContentOutFields):
    slug: str
    title: str
    summary: str
    body: str
    category: ProjectCategory
    tags: list[str]
    tech_stack: list[str]
    links: ProjectLinks
    featured: bool
    published_at: datetime | None
    cover: MediaOut | None


# ---------- Service (freelance offering) ----------
class ServiceIn(ContentFields):
    title: ShortText = Field(min_length=1)
    summary: str = Field(min_length=1, max_length=400)
    description: str = ""
    deliverables: list[Annotated[str, Field(max_length=200)]] = []
    pricing_note: ShortText = ""


class ServicePatch(ContentPatchFields):
    title: ShortText | None = Field(default=None, min_length=1)
    summary: str | None = Field(default=None, min_length=1, max_length=400)
    description: str | None = None
    deliverables: list[Annotated[str, Field(max_length=200)]] | None = None
    pricing_note: ShortText | None = None


class ServiceOut(ContentOutFields):
    title: str
    summary: str
    description: str
    deliverables: list[str]
    pricing_note: str


# ---------- Experience ----------
class _DateRange(BaseModel):
    start_date: date | None
    end_date: date | None

    @model_validator(mode="after")
    def _end_after_start(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ExperienceIn(ContentFields, _DateRange):
    type: ExperienceType
    organization: ShortText = Field(min_length=1)
    role: ShortText = Field(min_length=1)
    location: ShortText = ""
    start_date: date
    end_date: date | None = None
    bullets: list[Annotated[str, Field(max_length=300)]] = []


class ExperiencePatch(ContentPatchFields, _DateRange):
    type: ExperienceType | None = None
    organization: ShortText | None = Field(default=None, min_length=1)
    role: ShortText | None = Field(default=None, min_length=1)
    location: ShortText | None = None
    start_date: date | None = None
    end_date: date | None = None
    bullets: list[Annotated[str, Field(max_length=300)]] | None = None


class ExperienceOut(ContentOutFields):
    type: ExperienceType
    organization: str
    role: str
    location: str
    start_date: date
    end_date: date | None
    bullets: list[str]


# ---------- Skill ----------
class SkillIn(ContentFields):
    name: ShortText = Field(min_length=1, max_length=100)
    category: SkillCategory
    years: Years = 0
    proficiency: Proficiency = 3
    featured: bool = False


class SkillPatch(ContentPatchFields):
    name: ShortText | None = Field(default=None, min_length=1, max_length=100)
    category: SkillCategory | None = None
    years: Years | None = None
    proficiency: Proficiency | None = None
    featured: bool | None = None


class SkillOut(ContentOutFields):
    name: str
    category: SkillCategory
    years: float
    proficiency: int
    featured: bool


# ---------- Post ----------
class PostIn(ContentFields):
    slug: Slug | None = Field(default=None, description="Generated from the title if omitted")
    title: ShortText = Field(min_length=1)
    summary: str = Field(min_length=1, max_length=400)
    body: str = ""
    tags: list[Tag] = []
    cover_id: uuid.UUID | None = None


class PostPatch(ContentPatchFields):
    slug: Slug | None = None
    title: ShortText | None = Field(default=None, min_length=1)
    summary: str | None = Field(default=None, min_length=1, max_length=400)
    body: str | None = None
    tags: list[Tag] | None = None
    cover_id: uuid.UUID | None = None


class PostOut(ContentOutFields):
    slug: str
    title: str
    summary: str
    body: str
    tags: list[str]
    published_at: datetime | None
    cover: MediaOut | None
