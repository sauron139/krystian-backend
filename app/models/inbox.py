from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPk, str_enum
from app.models.enums import ContactIntent, MessageStatus


class ContactMessage(UUIDPk, Timestamps, Base):
    """A lead from the public contact form."""

    __tablename__ = "contact_messages"

    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    intent: Mapped[ContactIntent] = mapped_column(str_enum(ContactIntent, "contact_intent"))
    company: Mapped[str | None] = mapped_column(String(200))
    budget_range: Mapped[str | None] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[MessageStatus] = mapped_column(
        str_enum(MessageStatus, "message_status"), default=MessageStatus.NEW, index=True
    )
