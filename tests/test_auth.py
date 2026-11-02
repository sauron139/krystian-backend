from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.auth import REFRESH_COOKIE
from app.services.auth import upsert_admin
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


async def post_with_refresh(client: AsyncClient, path: str, token: str) -> int:
    """Present exactly one refresh cookie (the jar may hold several from earlier responses)."""
    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE, token)
    return (await client.post(path)).status_code


async def login(client: AsyncClient, password: str = ADMIN_PASSWORD) -> tuple[int, dict]:  # type: ignore[type-arg]
    resp = await client.post(
        "/v1/admin/auth/login", json={"email": ADMIN_EMAIL, "password": password}
    )
    return resp.status_code, resp.json()


async def test_login_success_sets_httponly_refresh_cookie(
    client: AsyncClient, session: AsyncSession
) -> None:
    await upsert_admin(session, ADMIN_EMAIL, ADMIN_PASSWORD)
    resp = await client.post(
        "/v1/admin/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    cookie = resp.headers["set-cookie"]
    assert REFRESH_COOKIE in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert "Path=/v1/admin/auth" in cookie


async def test_login_wrong_password_and_unknown_email_look_identical(
    client: AsyncClient, session: AsyncSession
) -> None:
    await upsert_admin(session, ADMIN_EMAIL, ADMIN_PASSWORD)
    status1, body1 = await login(client, "wrong-password")
    resp = await client.post(
        "/v1/admin/auth/login", json={"email": "nobody@test.dev", "password": "x"}
    )
    assert status1 == resp.status_code == 401
    assert body1 == resp.json()
    assert body1["error"]["code"] == "unauthorized"


async def test_login_is_rate_limited(client: AsyncClient, session: AsyncSession) -> None:
    await upsert_admin(session, ADMIN_EMAIL, ADMIN_PASSWORD)
    for _ in range(10):
        status, _ = await login(client, "wrong")
        assert status == 401
    status, body = await login(client)  # even the right password is blocked now
    assert status == 429
    assert body["error"]["code"] == "rate_limited"


async def test_admin_routes_require_token(client: AsyncClient) -> None:
    assert (await client.get("/v1/admin/projects")).status_code == 401
    bad = await client.get("/v1/admin/projects", headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401


async def test_me(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    resp = await client.get("/v1/admin/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == ADMIN_EMAIL


async def test_refresh_rotates_and_detects_reuse(
    client: AsyncClient, session: AsyncSession
) -> None:
    await upsert_admin(session, ADMIN_EMAIL, ADMIN_PASSWORD)
    resp = await client.post(
        "/v1/admin/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    first = resp.cookies[REFRESH_COOKIE]

    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE, first)
    rotated = await client.post("/v1/admin/auth/refresh")
    assert rotated.status_code == 200
    second = rotated.cookies[REFRESH_COOKIE]
    assert second != first

    # Replaying the old token is treated as theft: it fails and kills the whole family...
    assert await post_with_refresh(client, "/v1/admin/auth/refresh", first) == 401
    # ...including the newer token that was issued from it.
    assert await post_with_refresh(client, "/v1/admin/auth/refresh", second) == 401


async def test_logout_revokes_refresh_token(client: AsyncClient, session: AsyncSession) -> None:
    await upsert_admin(session, ADMIN_EMAIL, ADMIN_PASSWORD)
    resp = await client.post(
        "/v1/admin/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    token = resp.cookies[REFRESH_COOKIE]
    assert await post_with_refresh(client, "/v1/admin/auth/logout", token) == 204
    assert await post_with_refresh(client, "/v1/admin/auth/refresh", token) == 401
