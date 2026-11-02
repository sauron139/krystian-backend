# Import every model here so Base.metadata knows all tables (Alembic relies on this).
from app.models.auth import AdminUser, RefreshToken
from app.models.content import (
    ContentMixin,
    Experience,
    Post,
    Profile,
    Project,
    ServiceOffering,
    SiteSettings,
    Skill,
)
from app.models.inbox import ContactMessage
from app.models.media import Media

__all__ = [
    "AdminUser",
    "ContactMessage",
    "ContentMixin",
    "Experience",
    "Media",
    "Post",
    "Profile",
    "Project",
    "RefreshToken",
    "ServiceOffering",
    "SiteSettings",
    "Skill",
]
