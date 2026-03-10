from datetime import datetime
import asyncio

from app.database.message_queue import MessageQueueDB
from app.models.schemas import WhatsAppMessage
from app.services.whatsapp import BaileysProvider


def test_recoverable_bridge_failure_retries_quickly(tmp_path):
    db = MessageQueueDB(db_path=str(tmp_path / "messages.db"))
    queue_id = db.enqueue_message(
        phone="+919999999999",
        message="retry me",
        provider="baileys",
        source="payment_reminder",
    )

    before = datetime.now()
    db.mark_message_failed(
        queue_id=queue_id,
        error_message="bridge_session_degraded_retryable: Baileys session crypto state is degraded",
    )

    message = db.get_message_by_id(queue_id)
    assert message is not None
    assert message["status"] == "retrying"
    next_retry_at = datetime.fromisoformat(str(message["next_retry_at"]))
    delay = (next_retry_at - before).total_seconds()
    assert 0 <= delay <= 10


def test_baileys_provider_blocks_send_when_bridge_is_degraded(monkeypatch):
    recovery_requests = []

    async def fake_get_status():
        return {
            "state": "connected",
            "sessionState": "degraded",
            "isDegraded": True,
            "degradedReason": "signal_bad_mac_storm",
        }

    async def fake_restart():
        recovery_requests.append("restart")
        return {"success": True}

    monkeypatch.setattr("app.services.whatsapp.baileys_bridge.get_status", fake_get_status)
    monkeypatch.setattr("app.services.whatsapp.baileys_bridge.restart", fake_restart)

    provider = BaileysProvider()
    result = asyncio.run(
        provider.send_message(
            WhatsAppMessage(
                to="+919999999999",
                body="payment reminder",
            )
        )
    )

    assert result.success is False
    assert "bridge_session_degraded_retryable" in (result.error or "")
    assert recovery_requests == ["restart"]
