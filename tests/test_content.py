from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("seeded")


async def test_seeded_public_content_is_flagged_placeholder(client: AsyncClient) -> None:
    profile = (await client.get("/v1/profile")).json()
    assert profile["is_placeholder"] is True
    projects = (await client.get("/v1/projects")).json()
    assert projects["total"] == 3
    assert all(p["is_placeholder"] for p in projects["items"])
    for path in ("/v1/services", "/v1/experience", "/v1/skills"):
        items = (await client.get(path)).json()
        assert items and all(i["is_placeholder"] for i in items)


async def test_drafts_are_hidden_from_public(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    draft = {"title": "Secret Draft", "summary": "Not yet", "category": "software"}
    resp = await client.post("/v1/admin/projects", json=draft, headers=admin_headers)
    assert resp.status_code == 201
    slug = resp.json()["slug"]
    assert slug == "secret-draft"
    assert (await client.get(f"/v1/projects/{slug}")).status_code == 404
    admin_list = (await client.get("/v1/admin/projects?status=draft", headers=admin_headers)).json()
    assert [p["slug"] for p in admin_list["items"]] == ["secret-draft"]


async def test_publish_flow_stamps_date_and_invalidates_cache(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    before = (await client.get("/v1/projects")).json()  # warms the cache
    body = {
        "title": "Orbit Lab",
        "summary": "N-body simulator",
        "category": "physics",
        "tags": ["simulation"],
        "links": {"repo": "https://github.com/example/orbit-lab"},
    }
    created = (await client.post("/v1/admin/projects", json=body, headers=admin_headers)).json()
    assert created["published_at"] is None

    patched = await client.patch(
        f"/v1/admin/projects/{created['id']}", json={"status": "published"}, headers=admin_headers
    )
    assert patched.status_code == 200
    assert patched.json()["published_at"] is not None

    after = (await client.get("/v1/projects")).json()
    assert after["total"] == before["total"] + 1  # cache was invalidated by the write
    one = (await client.get("/v1/projects/orbit-lab")).json()
    assert one["links"] == {
        "repo": "https://github.com/example/orbit-lab",
        "demo": None,
        "paper": None,
    }
    assert (await client.get("/v1/projects?tag=simulation")).json()["total"] == 1
    assert (await client.get("/v1/projects?category=software")).json()["total"] == 1  # seed


async def test_duplicate_titles_get_unique_slugs_and_explicit_dupes_conflict(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    body = {"title": "Same Name", "summary": "x", "category": "software"}
    a = (await client.post("/v1/admin/projects", json=body, headers=admin_headers)).json()
    b = (await client.post("/v1/admin/projects", json=body, headers=admin_headers)).json()
    assert (a["slug"], b["slug"]) == ("same-name", "same-name-2")
    dupe = await client.post(
        "/v1/admin/projects", json={**body, "slug": "same-name"}, headers=admin_headers
    )
    assert dupe.status_code == 409


async def test_editing_placeholder_clears_flag(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    services = (await client.get("/v1/admin/services", headers=admin_headers)).json()["items"]
    target = services[0]
    resp = await client.patch(
        f"/v1/admin/services/{target['id']}", json={"title": "Web apps"}, headers=admin_headers
    )
    assert resp.json()["is_placeholder"] is False
    public = (await client.get("/v1/services")).json()
    assert {s["title"]: s["is_placeholder"] for s in public}["Web apps"] is False


async def test_reorder(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    items = (await client.get("/v1/admin/services", headers=admin_headers)).json()["items"]
    ids = [i["id"] for i in reversed(items)]
    resp = await client.post("/v1/admin/services/reorder", json={"ids": ids}, headers=admin_headers)
    assert resp.status_code == 204
    public = (await client.get("/v1/services")).json()
    assert [s["id"] for s in public] == ids


async def test_validation_errors_use_standard_shape(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/admin/skills",
        json={"name": "Go", "category": "language", "proficiency": 9},
        headers=admin_headers,
    )
    assert resp.status_code == 422
    err: dict[str, Any] = resp.json()["error"]
    assert err["code"] == "validation_error"
    assert any(f["loc"][-1] == "proficiency" for f in err["details"]["fields"])

    bad_dates = await client.post(
        "/v1/admin/experience",
        json={"type": "work", "organization": "A", "role": "B",
              "start_date": "2025-01-01", "end_date": "2024-01-01"},
        headers=admin_headers,
    )  # fmt: skip
    assert bad_dates.status_code == 422


async def test_delete(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    items = (await client.get("/v1/admin/skills", headers=admin_headers)).json()
    first = items["items"][0]["id"]
    assert (
        await client.delete(f"/v1/admin/skills/{first}", headers=admin_headers)
    ).status_code == 204
    assert (await client.get(f"/v1/admin/skills/{first}", headers=admin_headers)).status_code == 404
    assert len((await client.get("/v1/skills")).json()) == items["total"] - 1


async def test_profile_and_checklist(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    checklist = (await client.get("/v1/admin/content-checklist", headers=admin_headers)).json()
    assert checklist["completed"] == 0
    assert checklist["placeholder_counts"]["projects"] == 3

    profile = {
        "full_name": "Krystian Nmeze",
        "headline": "Software engineer & physics student",
        "short_bio": "I build software and study physics.",
        "socials": {"github": "https://github.com/sauron139"},
    }
    resp = await client.put("/v1/admin/profile", json=profile, headers=admin_headers)
    assert resp.status_code == 200
    public = (await client.get("/v1/profile")).json()
    assert public["full_name"] == "Krystian Nmeze" and public["is_placeholder"] is False
    assert public["socials"]["github"] == "https://github.com/sauron139"

    checklist = (await client.get("/v1/admin/content-checklist", headers=admin_headers)).json()
    done = {i["key"]: i["done"] for i in checklist["items"]}
    assert done["profile_bio"] is True and done["profile_photo"] is False


async def test_unknown_media_reference_rejected(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/admin/projects",
        json={"title": "X", "summary": "Y", "category": "software",
              "cover_id": "00000000-0000-0000-0000-000000000000"},
        headers=admin_headers,
    )  # fmt: skip
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_reference"
