from typing import Any

import pytest
from httpx import AsyncClient

from app.services import contact as contact_service

VALID: dict[str, Any] = {
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "intent": "freelance",
    "budget_range": "$2k to $10k",
    "message": "I'd like a simulation dashboard for our lab.",
}


async def test_contact_stores_lead_and_appears_in_inbox(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.post("/v1/contact", json=VALID)
    assert resp.status_code == 202
    inbox = (await client.get("/v1/admin/messages", headers=admin_headers)).json()
    assert inbox["total"] == 1
    msg = inbox["items"][0]
    assert msg["status"] == "new" and msg["intent"] == "freelance"

    patched = await client.patch(
        f"/v1/admin/messages/{msg['id']}", json={"status": "replied"}, headers=admin_headers
    )
    assert patched.json()["status"] == "replied"
    new_only = (await client.get("/v1/admin/messages?status=new", headers=admin_headers)).json()
    assert new_only["total"] == 0


async def test_honeypot_is_silently_dropped(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.post("/v1/contact", json={**VALID, "website": "http://spam.example"})
    assert resp.status_code == 202  # bot sees success...
    inbox = (await client.get("/v1/admin/messages", headers=admin_headers)).json()
    assert inbox["total"] == 0  # ...but nothing is stored


async def test_contact_rate_limit(client: AsyncClient) -> None:
    for _ in range(5):
        assert (await client.post("/v1/contact", json=VALID)).status_code == 202
    blocked = await client.post("/v1/contact", json=VALID)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


async def test_contact_validation(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/contact", json={**VALID, "email": "not-an-email", "message": "hi"}
    )
    assert resp.status_code == 422
    bad = {f["loc"][-1] for f in resp.json()["error"]["details"]["fields"]}
    assert bad == {"email", "message"}


async def test_notification_email_sent_when_configured(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict[str, Any]] = []

    async def fake_send(**kwargs: Any) -> None:
        sent.append(kwargs)

    class FakeSettings:
        notify_email = "owner@example.com"

    monkeypatch.setattr(contact_service, "send_email", fake_send)
    monkeypatch.setattr(contact_service, "get_settings", lambda: FakeSettings())
    # receive_message also reads settings for rate limits; give it the real values.
    from app.core.config import get_settings as real

    async def receive(session: Any, data: Any, ip: str) -> Any:
        monkeypatch.setattr(contact_service, "get_settings", real)
        try:
            return await original(session, data, ip)
        finally:
            monkeypatch.setattr(contact_service, "get_settings", lambda: FakeSettings())

    original = contact_service.receive_message
    monkeypatch.setattr(contact_service, "receive_message", receive)

    assert (await client.post("/v1/contact", json=VALID)).status_code == 202
    assert len(sent) == 1
    assert sent[0]["to"] == "owner@example.com"
    assert sent[0]["reply_to"] == "ada@example.com"
    assert "freelance" in sent[0]["subject"]
