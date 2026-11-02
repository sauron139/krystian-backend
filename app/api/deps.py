from typing import Annotated

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import unauthorized
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import AdminUser

SessionDep = Annotated[AsyncSession, Depends(get_session)]
_bearer = HTTPBearer(auto_error=False)


async def current_admin(
    session: SessionDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AdminUser:
    if creds is None:
        raise unauthorized()
    user_id = decode_access_token(creds.credentials)
    user = await session.get(AdminUser, user_id) if user_id else None
    if user is None or not user.is_active:
        raise unauthorized("Invalid or expired token")
    return user


AdminDep = Annotated[AdminUser, Depends(current_admin)]


def client_ip(request: Request) -> str:
    # Behind Caddy, uvicorn's --proxy-headers sets request.client from X-Forwarded-For.
    return request.client.host if request.client else "unknown"


ClientIP = Annotated[str, Depends(client_ip)]


class Pagination:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> None:
        self.page = page
        self.page_size = page_size


PageDep = Annotated[Pagination, Depends()]
