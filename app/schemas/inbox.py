import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import ContactIntent, MessageStatus
from app.schemas.common import ORMModel, ShortText


class ContactIn(BaseModel):
    name: ShortText = Field(min_length=1, max_length=120)
    email: EmailStr
    intent: ContactIntent
    company: ShortText | None = None
    budget_range: str | None = Field(default=None, max_length=60)
    message: str = Field(min_length=10, max_length=5000)
    # Honeypot: hidden in the form; humans leave it empty, naive bots fill it in.
    website: str = Field(default="", max_length=200)
    turnstile_token: str | None = Field(default=None, max_length=4096)


class ContactAccepted(BaseModel):
    status: Literal["received"] = "received"


class MessageOut(ORMModel):
    id: uuid.UUID
    name: str
    email: str
    intent: ContactIntent
    company: str | None
    budget_range: str | None
    message: str
    status: MessageStatus
    created_at: datetime


class MessagePatch(BaseModel):
    status: MessageStatus
