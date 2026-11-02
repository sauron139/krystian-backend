import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rate_limit
from app.core.config import get_settings
from app.core.errors import unauthorized
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.models import AdminUser, RefreshToken


async def authenticate(
    session: AsyncSession, email: str, password: str, client_ip: str
) -> AdminUser:
    settings = get_settings()
    limit_key = f"login:{client_ip}"
    await rate_limit.enforce(
        limit_key, settings.login_rate_limit, settings.login_rate_window_seconds
    )
    user = await session.scalar(select(AdminUser).where(AdminUser.email == email.lower()))
    ok = verify_password(password, user.password_hash if user else None)
    if not user or not ok or not user.is_active:
        raise unauthorized("Invalid email or password")
    await rate_limit.reset(limit_key)
    user.last_login_at = datetime.now(UTC)
    await session.commit()
    return user


async def issue_tokens(
    session: AsyncSession, user: AdminUser, family_id: uuid.UUID | None = None
) -> tuple[str, int, str]:
    """Return (access_token, expires_in, raw_refresh_token)."""
    raw = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_ttl_days),
        )
    )
    await session.commit()
    access, expires_in = create_access_token(user.id)
    return access, expires_in, raw


async def rotate_refresh_token(session: AsyncSession, raw: str) -> tuple[str, int, str]:
    token = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))
    )
    if token is None:
        raise unauthorized("Session expired. Sign in again.")
    if token.revoked_at is not None:
        # A revoked token came back: it was copied. Kill every token in its family.
        await revoke_family(session, token.family_id)
        raise unauthorized("Session expired. Sign in again.")
    if token.expires_at <= datetime.now(UTC):
        raise unauthorized("Session expired. Sign in again.")
    user = await session.get(AdminUser, token.user_id)
    if user is None or not user.is_active:
        raise unauthorized("Session expired. Sign in again.")
    token.revoked_at = datetime.now(UTC)
    return await issue_tokens(session, user, token.family_id)


async def revoke_family(session: AsyncSession, family_id: uuid.UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()


async def logout(session: AsyncSession, raw: str | None) -> None:
    if not raw:
        return
    token = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))
    )
    if token is not None:
        await revoke_family(session, token.family_id)


async def upsert_admin(session: AsyncSession, email: str, password: str) -> AdminUser:
    """Create the admin user, or reset its password if it exists."""
    email = email.lower()
    user = await session.scalar(select(AdminUser).where(AdminUser.email == email))
    if user is None:
        user = AdminUser(email=email, password_hash=hash_password(password))
        session.add(user)
    else:
        user.password_hash = hash_password(password)
        user.is_active = True
    await session.commit()
    return user
