import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, HttpUrl

from app.models.enums import Availability
from app.schemas.common import MediaOut, ORMModel, ShortText


class Socials(BaseModel):
    github: HttpUrl | None = None
    linkedin: HttpUrl | None = None
    x: HttpUrl | None = None
    website: HttpUrl | None = None


class ProfileIn(BaseModel):
    full_name: ShortText = Field(min_length=1, max_length=120)
    headline: ShortText = Field(min_length=1)
    short_bio: str = Field(min_length=1, max_length=600)
    long_bio: str = ""
    location: ShortText = ""
    email: EmailStr | None = None
    socials: Socials = Socials()
    availability: Availability = Availability.OPEN_TO_BOTH
    photo_id: uuid.UUID | None = None
    cv_id: uuid.UUID | None = None


class ProfileOut(ORMModel):
    full_name: str
    headline: str
    short_bio: str
    long_bio: str
    location: str
    email: str
    socials: Socials
    availability: Availability
    photo: MediaOut | None
    cv: MediaOut | None
    is_placeholder: bool
    updated_at: datetime


class SiteSettingsIn(BaseModel):
    seo_title: ShortText = Field(min_length=1, max_length=120)
    seo_description: str = Field(min_length=1, max_length=300)
    show_blog: bool = False
    show_cv_button: bool = False
    og_image_id: uuid.UUID | None = None


class SiteSettingsOut(ORMModel):
    seo_title: str
    seo_description: str
    show_blog: bool
    show_cv_button: bool
    og_image: MediaOut | None
    is_placeholder: bool
    updated_at: datetime


class ChecklistItem(BaseModel):
    key: str
    label: str
    done: bool


class ContentChecklist(BaseModel):
    items: list[ChecklistItem]
    completed: int
    total: int
    placeholder_counts: dict[str, int]
