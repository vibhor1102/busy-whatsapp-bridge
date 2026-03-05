import asyncio
from types import SimpleNamespace

from app.database.message_queue import MessageQueueDB
from app.services.reminder_service import reminder_service


def _build_session():
    metrics = SimpleNamespace(
        total_messages=4,
        sent_count=2,
        failed_count=2,
        avg_delay_seconds=1.2,
        typing_time_total=10.0,
        reading_time_total=8.0,
        duration_seconds=95.0,
    )
    return SimpleNamespace(session_id="sess-report", metrics=metrics)


def test_session_report_includes_failure_details_and_unsaved_contacts(monkeypatch, tmp_path):
    db = MessageQueueDB(db_path=str(tmp_path / "report.db"))
    monkeypatch.setattr("app.services.reminder_service.message_db", db)

    cfg = SimpleNamespace(admin_phone="+917206366664", typing_simulation=True)
    monkeypatch.setattr("app.services.reminder_service.anti_spam_service.get_config", lambda: cfg)

    batch_id = "batch-report-1"
    db.create_reminder_batch(
        batch_id=batch_id,
        session_id="sess-report",
        company_id="default",
        template_id="standard",
        sent_by="manual",
        total_parties=4,
    )
    db.upsert_reminder_batch_recipient(
        batch_id=batch_id,
        party_code="P1",
        recipient_name="Alpha Traders",
        phone="+919876543210",
        status="failed",
        queue_status="failed",
        delivery_status="failed",
        failure_stage="delivery_webhook",
        failure_code="delivery_failed",
        failure_message="recipient not found",
        contact_state="likely_unsaved",
    )
    db.upsert_reminder_batch_recipient(
        batch_id=batch_id,
        party_code="P2",
        recipient_name="Beta Stores",
        phone="+919812345678",
        status="failed",
        queue_status="failed",
        delivery_status="failed",
        failure_stage="validation",
        failure_code="invalid_phone",
        failure_message="phone length invalid after normalization",
        contact_state="unknown",
    )

    asyncio.run(reminder_service._send_session_report(_build_session(), batch_id=batch_id))
    rows = db.get_pending_messages(limit=50)
    reports = [r for r in rows if r.get("source") == "admin_report"]
    assert reports, "Expected admin report message(s)"
    text = "\n".join(r["message"] for r in reports)
    assert "Failed Recipients" in text
    assert "Alpha Traders" in text and "+919876543210" in text
    assert "delivery_webhook" in text and "delivery_failed" in text
    assert "Not Saved / Likely Unsaved Contacts" in text


def test_session_report_chunks_when_large(monkeypatch, tmp_path):
    db = MessageQueueDB(db_path=str(tmp_path / "report_chunks.db"))
    monkeypatch.setattr("app.services.reminder_service.message_db", db)

    cfg = SimpleNamespace(admin_phone="+917206366664", typing_simulation=True)
    monkeypatch.setattr("app.services.reminder_service.anti_spam_service.get_config", lambda: cfg)

    batch_id = "batch-report-2"
    db.create_reminder_batch(
        batch_id=batch_id,
        session_id="sess-report",
        company_id="default",
        template_id="standard",
        sent_by="manual",
        total_parties=120,
    )
    for i in range(120):
        db.upsert_reminder_batch_recipient(
            batch_id=batch_id,
            party_code=f"P{i}",
            recipient_name=f"Customer {i}",
            phone=f"+91999999{i:04d}"[-13:],
            status="failed",
            queue_status="failed",
            delivery_status="failed",
            failure_stage="delivery_webhook",
            failure_code="delivery_failed",
            failure_message="recipient not found in whatsapp",
            contact_state="likely_unsaved",
        )

    asyncio.run(reminder_service._send_session_report(_build_session(), batch_id=batch_id))
    rows = db.get_pending_messages(limit=500)
    reports = [r for r in rows if r.get("source") == "admin_report"]
    assert len(reports) > 1
