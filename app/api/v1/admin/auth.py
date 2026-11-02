from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status

from app.api.deps import AdminDep, ClientIP, SessionDep
from app.core.config import get_settings
from app.core.errors import unauthorized
from app.models import AdminUser
from app.schemas.auth import AdminOut, LoginIn, TokenOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["admin: auth"])

REFRESH_COOKIE = "krystian_refresh"
COOKIE_PATH = "/v1/admin/auth"  # the browser only sends the cookie to these endpoints


def _set_refresh_cookie(response: Response, raw: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=settings.refresh_token_ttl_days * 86400,
        path=COOKIE_PATH,
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,  # JavaScript can't read it, so XSS can't steal it
        samesite="strict",  # never sent on cross-site requests, which blocks CSRF
    )


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, response: Response, session: SessionDep, ip: ClientIP) -> TokenOut:
    user = await auth_service.authenticate(session, data.email, data.password, ip)
    access, expires_in, refresh = await auth_service.issue_tokens(session, user)
    _set_refresh_cookie(response, refresh)
    return TokenOut(access_token=access, expires_in=expires_in)


@router.post("/refresh", response_model=TokenOut)
async def refresh(
    response: Response,
    session: SessionDep,
    token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> TokenOut:
    if not token:
        raise unauthorized("Session expired. Sign in again.")
    access, expires_in, new_refresh = await auth_service.rotate_refresh_token(session, token)
    _set_refresh_cookie(response, new_refresh)
    return TokenOut(access_token=access, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session: SessionDep,
    token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> None:
    await auth_service.logout(session, token)
    settings = get_settings()
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH, domain=settings.cookie_domain)


@router.get("/me", response_model=AdminOut)
async def me(admin: AdminDep) -> AdminUser:
    return admin
