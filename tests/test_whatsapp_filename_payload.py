import asyncio

from app.models.schemas import WhatsAppMessage
from app.services.whatsapp import BaileysProvider


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._payload


def test_baileys_media_payload_includes_filename(monkeypatch):
    captured_posts = []

    class _FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, timeout):
            return _FakeResponse(200, {"data": {"state": "connected"}})

        async def post(self, url, json, timeout):
            captured_posts.append({"url": url, "json": json, "timeout": timeout})
            return _FakeResponse(200, {"data": {"messageId": "wamid.X1"}})

    monkeypatch.setattr("app.services.whatsapp.httpx.AsyncClient", _FakeAsyncClient)

    provider = BaileysProvider()
    msg = WhatsAppMessage(
        to="+919999999999",
        body="Invoice attached",
        media_url="https://example.com/x.pdf",
        file_name="acme_invoice_05-03-2026.pdf",
    )

    result = asyncio.run(provider.send_message(msg))
    assert result.success is True
    assert captured_posts, "Expected send-media POST call"
    payload = captured_posts[-1]["json"]
    assert payload["fileName"] == "acme_invoice_05-03-2026.pdf"
