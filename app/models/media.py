from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPk


class Media(UUIDPk, Timestamps, Base):
    """Metadata for an uploaded file. Uploads arrive in Milestone 4; the table exists now
    so profile/projects can reference media from the start."""

    __tablename__ = "media"

    key: Mapped[str] = mapped_column(String(300), unique=True)  # object-storage key
    url: Mapped[str] = mapped_column(String(600))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    width: Mapped[int | None]
    height: Mapped[int | None]
    alt_text: Mapped[str] = mapped_column(String(300), default="")
