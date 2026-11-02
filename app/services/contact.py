import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rate_limit
from app.core.config import get_settings
from app.core.email import send_email
from app.core.errors import AppError
from app.models import ContactMessage
from app.schemas.inbox import ContactIn

log = logging.getLogger(__name__)
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str | None, client_ip: str) -> bool:
    secret = get_settings().turnstile_secret
    if secret is None:
        return True  # not configured (local dev / tests)
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                TURNSTILE_VERIFY_URL,
                data={
                    "secret": secret.get_secret_value(),
                    "response": token,
                    "remoteip": client_ip,
                },
            )
        return bool(resp.json().get("success"))
    except (httpx.HTTPError, ValueError):
        log.warning("turnstile verification failed", exc_info=True)
        return False


async def receive_message(
    session: AsyncSession, data: ContactIn, client_ip: str
) -> ContactMessage | None:
    """Store a lead. Returns None (silently) for honeypot hits so bots learn nothing."""
    settings = get_settings()
    await rate_limit.enforce(
        f"contact:{client_ip}", settings.contact_rate_limit, settings.contact_rate_window_seconds
    )
    if data.website.strip():
        log.info("contact honeypot triggered from %s", client_ip)
        return None
    if not await verify_turnstile(data.turnstile_token, client_ip):
        raise AppError(400, "captcha_failed", "Verification failed. Refresh the page and retry.")

    msg = ContactMessage(
        name=data.name,
        email=str(data.email),
        intent=data.intent,
        company=data.company,
        budget_range=data.budget_range,
        message=data.message,
    )
    session.add(msg)
    await session.commit()
    return msg


async def notify_new_message(msg_id: str, name: str, email: str, intent: str, body: str) -> None:
    to = get_settings().notify_email
    if to is None:
        return
    await send_email(
        to=str(to),
        subject=f"New {intent} enquiry from {name}",
        body=f"From: {name} <{email}>\nIntent: {intent}\nID: {msg_id}\n\n{body}\n",
        reply_to=email,
    )
