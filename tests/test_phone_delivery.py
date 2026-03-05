from pathlib import Path
from datetime import datetime, timedelta

import pytest

from app.database.message_queue import MessageQueueDB
from app.utils.phone import normalize_indian_phone_local, normalize_phone_e164, to_wa_id


def test_indian_local_number_normalization():
    assert normalize_indian_phone_local("9215536993") == "9215536993"
    assert normalize_phone_e164("9215536993") == "+919215536993"
    assert to_wa_id("9215536993") == "919215536993"
    assert normalize_phone_e164("09215536993") == "+919215536993"
    assert normalize_phone_e164("+91 92155 36993") == "+919215536993"
    assert normalize_phone_e164("91-92155-36993") == "+919215536993"
    assert normalize_phone_e164("0091 92155 36993") == "+919215536993"
    assert normalize_phone_e164("000919215536993") == "+919215536993"


def test_indian_phone_rejection_rules():
    with pytest.raises(ValueError, match="phone length invalid"):
        normalize_phone_e164("921553699")
    with pytest.raises(ValueError, match="phone is not a valid Indian mobile"):
        normalize_phone_e164("5215536993")
    with pytest.raises(ValueError, match="phone has no digits"):
        normalize_phone_e164("abc")
    with pytest.raises(ValueError, match="phone is not a valid Indian mobile"):
        normalize_phone_e164("+14155552671")


def test_delivery_status_lifecycle_update(tmp_path: Path):
    db = MessageQueueDB(db_path=str(tmp_path / "messages.db"))

    queue_id = db.enqueue_message(
        phone="9215536993",
        message="Test reminder",
        provider="baileys",
        source="payment_reminder",
    )
    db.mark_message_sent(
        queue_id=queue_id,
        message_id="wamid.TEST123",
        provider="baileys",
        delivery_status="accepted",
        resolved_phone="+919215536993",
    )

    rows = db.get_message_history(source="payment_reminder", limit=5)
    assert len(rows) == 1
    assert rows[0]["status"] == "sent"
    assert rows[0]["delivery_status"] == "accepted"
    assert rows[0]["delivered_at"] is None
    assert rows[0]["read_at"] is None
    assert rows[0]["phone"] == "+919215536993"

    # REMOVED: Meta webhook status updates - only Baileys available now
    # Test update from "delivered" to another state (if applicable)
    # assert db.update_delivery_status(
    #     message_id="wamid.TEST123",
    #     delivery_status="delivered",
    #     recipient_waid="919215536993",
    #     provider="baileys",
    # )
    # delivered = db.get_message_history(source="payment_reminder", limit=1)[0]
    # assert delivered["status"] == "sent"
    # assert delivered["delivery_status"] == "delivered"
    # assert delivered["delivered_at"] is not None


# REMOVED: test_meta_webhook_diagnostics_and_history_time_filters
# Meta webhook methods have been removed - only Baileys available
# TODO: Re-add via Baileys integration when needed
# def test_meta_webhook_diagnostics_and_history_time_filters(tmp_path: Path):
#     ...

def test_baileys_delivery_and_history_time_filters(tmp_path: Path):
    """Test delivery status and history time filters with Baileys provider."""
    db = MessageQueueDB(db_path=str(tmp_path / "messages.db"))
    now = datetime.now()

    qid = db.enqueue_message(
        phone="+919999999999",
        message="hello",
        provider="baileys",
        source="payment_reminder",
    )
    db.mark_message_sent(
        queue_id=qid,
        message_id="wamid.TS1",
        provider="baileys",
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


def test_delivery_status_monotonic_and_idempotent(tmp_path: Path):
    db = MessageQueueDB(db_path=str(tmp_path / "messages.db"))
    qid = db.enqueue_message(
        phone="+919999999999",
        message="status flow",
        provider="baileys",
        source="payment_reminder",
    )
    db.mark_message_sent(
        queue_id=qid,
        message_id="wamid.MONO1",
        provider="baileys",
        delivery_status="accepted",
        resolved_phone="+919999999999",
    )

    assert db.update_delivery_status(message_id="wamid.MONO1", delivery_status="delivered")
    assert db.update_delivery_status(message_id="wamid.MONO1", delivery_status="sent")
    # Non-monotonic downgrade should be ignored; remains delivered.
    row = db.get_message_history(source="payment_reminder", limit=1)[0]
    assert row["delivery_status"] == "delivered"

    assert db.update_delivery_status(message_id="wamid.MONO1", delivery_status="read")
    assert db.update_delivery_status(message_id="wamid.MONO1", delivery_status="read")
    row = db.get_message_history(source="payment_reminder", limit=1)[0]
    assert row["delivery_status"] == "read"
