from pathlib import Path
from datetime import datetime, timedelta

from app.database.message_queue import MessageQueueDB
from app.utils.phone import normalize_phone_e164, to_wa_id


def test_indian_local_number_normalization():
    assert normalize_phone_e164("9215536993") == "+919215536993"
    assert to_wa_id("9215536993") == "919215536993"
    assert normalize_phone_e164("09215536993") == "+919215536993"
    assert normalize_phone_e164("+14155552671") == "+14155552671"


def test_delivery_status_lifecycle_update(tmp_path: Path):
    db = MessageQueueDB(db_path=str(tmp_path / "messages.db"))

    queue_id = db.enqueue_message(
        phone="9215536993",
        message="Test reminder",
        provider="meta",
        source="payment_reminder",
    )
    db.mark_message_sent(
        queue_id=queue_id,
        message_id="wamid.TEST123",
        provider="meta",
        delivery_status="accepted",
        resolved_phone="+919215536993",
    )

    rows = db.get_message_history(source="payment_reminder", limit=5)
    assert len(rows) == 1
    assert rows[0]["status"] == "sent"
    assert rows[0]["delivery_status"] == "accepted"
    assert rows[0]["phone"] == "+919215536993"

    assert db.update_delivery_status(
        message_id="wamid.TEST123",
        delivery_status="delivered",
        recipient_waid="919215536993",
        provider="meta",
    )
    delivered = db.get_message_history(source="payment_reminder", limit=1)[0]
    assert delivered["status"] == "sent"
    assert delivered["delivery_status"] == "delivered"
    assert delivered["delivered_at"] is not None

    assert db.update_delivery_status(
        message_id="wamid.TEST123",
        delivery_status="failed",
        error_message="[131026] undeliverable",
        recipient_waid="919215536993",
        provider="meta",
    )
    failed = db.get_message_history(source="payment_reminder", limit=1)[0]
    assert failed["status"] == "failed"
    assert failed["delivery_status"] == "failed"
    assert failed["failed_at"] is not None
    assert "131026" in (failed["error_message"] or "")


def test_meta_webhook_diagnostics_and_history_time_filters(tmp_path: Path):
    db = MessageQueueDB(db_path=str(tmp_path / "messages.db"))
    now = datetime.now()

    db.record_meta_webhook_verify(success=True, mode="subscribe", source_ip="1.2.3.4")
    db.record_meta_webhook_error(
        source_ip="1.2.3.4",
        stage="status_apply",
        error_message="test error",
        payload={"id": "abc"},
    )
    db.record_meta_webhook_post(source_ip="5.6.7.8", last_status="delivered", updates=2)

    status = db.get_meta_webhook_status(error_limit=5)
    assert status["verified_config"] is True
    assert status["last_verify_mode"] == "subscribe"
    assert status["last_webhook_post_source_ip"] == "5.6.7.8"
    assert status["last_webhook_delivery_status_seen"] == "delivered"
    assert len(status["recent_errors"]) >= 1

    qid = db.enqueue_message(
        phone="+919999999999",
        message="hello",
        provider="meta",
        source="payment_reminder",
    )
    db.mark_message_sent(
        queue_id=qid,
        message_id="wamid.TS1",
        provider="meta",
        delivery_status="accepted",
        resolved_phone="+919999999999",
    )

    rows = db.get_message_history(
        source="payment_reminder",
        from_time=now - timedelta(minutes=1),
        to_time=now + timedelta(minutes=1),
        limit=10,
    )
    assert len(rows) >= 1
