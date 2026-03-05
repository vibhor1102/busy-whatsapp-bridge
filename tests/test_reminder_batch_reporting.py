from app.database.message_queue import MessageQueueDB


def test_batch_report_aggregates(tmp_path):
    db = MessageQueueDB(db_path=str(tmp_path / "batch_report.db"))
    batch_id = "batch-1"
    db.create_reminder_batch(
        batch_id=batch_id,
        session_id="sess-1",
        company_id="default",
        template_id="standard",
        sent_by="manual",
        total_parties=3,
    )

    db.upsert_reminder_batch_recipient(
        batch_id=batch_id,
        party_code="P001",
        status="queued",
        queue_status="queued",
        delivery_status="accepted",
    )
    db.upsert_reminder_batch_recipient(
        batch_id=batch_id,
        party_code="P002",
        status="failed",
        queue_status="failed",
        delivery_status="failed",
        failure_stage="validation",
        failure_code="no_phone_number",
    )
    db.upsert_reminder_batch_recipient(
        batch_id=batch_id,
        party_code="P003",
        status="skipped",
        queue_status="skipped",
        failure_stage="validation",
        failure_code="amount_due_not_positive",
    )

    report = db.get_reminder_batch_report(batch_id)
    assert report is not None
    assert report["batch"]["queue_success_count"] == 1
    assert report["batch"]["queue_failed_count"] == 1
    assert report["batch"]["skipped_count"] == 1
    assert report["batch"]["delivery_accepted_count"] == 1
    assert report["batch"]["delivery_failed_count"] == 1


def test_queue_link_updates_recipient_status(tmp_path):
    db = MessageQueueDB(db_path=str(tmp_path / "batch_link.db"))
    batch_id = "batch-2"
    db.create_reminder_batch(
        batch_id=batch_id,
        session_id="sess-2",
        company_id="default",
        template_id="standard",
        sent_by="manual",
        total_parties=1,
    )
    db.upsert_reminder_batch_recipient(
        batch_id=batch_id,
        party_code="P100",
        status="queued",
        queue_status="queued",
    )
    queue_id = db.enqueue_message(
        phone="+919234567890",
        message="hello",
        provider="baileys",
        source="payment_reminder",
        batch_id=batch_id,
        party_code="P100",
    )
    db.mark_message_sent(
        queue_id=queue_id,
        message_id="wamid-1",
        provider="baileys",
        delivery_status="accepted",
        resolved_phone="+919234567890",
        contact_name="Alpha",
        contact_source="contact_cache",
        contact_is_saved=True,
        contact_state="saved",
    )
    db.update_delivery_status(
        message_id="wamid-1",
        delivery_status="failed",
        error_message="blocked",
        contact_name="Alpha",
        contact_source="delivery_cache",
        contact_is_saved=False,
        contact_state="likely_unsaved",
    )
    failures = db.get_reminder_batch_failures(batch_id=batch_id)
    assert len(failures) == 1
    assert failures[0]["failure_stage"] == "delivery_webhook"
    assert failures[0]["failure_code"] == "delivery_failed"
    assert failures[0]["contact_name"] == "Alpha"
    assert failures[0]["contact_source"] == "delivery_cache"
    assert failures[0]["contact_state"] == "likely_unsaved"
