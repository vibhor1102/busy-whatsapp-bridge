from pathlib import Path

from app.database.message_queue import MessageQueueDB


def test_file_name_persists_queue_to_history_and_dead_letter(tmp_path: Path):
    db = MessageQueueDB(db_path=str(tmp_path / "messages.db"))

    queue_id = db.enqueue_message(
        phone="+919999999999",
        message="Invoice test",
        pdf_url="https://example.com/invoice.pdf",
        file_name="abc_invoice_05-03-2026.pdf",
        provider="baileys",
        source="test",
    )

    pending = db.get_pending_messages(limit=10)
    current = next(row for row in pending if row["id"] == queue_id)
    assert current["file_name"] == "abc_invoice_05-03-2026.pdf"

    db.mark_message_sent(
        queue_id=queue_id,
        message_id="wamid.FILE1",
        provider="baileys",
    )
    history = db.get_message_history(limit=10)
    sent = next(row for row in history if row["queue_id"] == queue_id)
    assert sent["file_name"] == "abc_invoice_05-03-2026.pdf"

    dead_id = db.enqueue_message(
        phone="+918888888888",
        message="Force dead letter",
        pdf_url="https://example.com/doc.pdf",
        file_name="ledger_05-03-2026.pdf",
        provider="baileys",
        source="test",
    )
    for _ in range(5):
        db.mark_message_failed(queue_id=dead_id, error_message="test failure")

    dead_rows = db.get_dead_letter_messages(limit=10)
    dead = next(row for row in dead_rows if row["queue_id"] == dead_id)
    assert dead["file_name"] == "ledger_05-03-2026.pdf"
