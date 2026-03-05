from pathlib import Path

from app.database.message_queue import MessageQueueDB


def test_test_source_cleanup_runs_once_and_preserves_non_test(tmp_path: Path):
    db_path = tmp_path / "messages.db"
    db = MessageQueueDB(db_path=str(db_path))

    # Insert mixed sources.
    test_qid = db.enqueue_message(
        phone="+919111111111",
        message="test pending",
        provider="baileys",
        source="test",
    )
    keep_qid = db.enqueue_message(
        phone="+917222222222",
        message="keep pending",
        provider="baileys",
        source="api",
    )
    db.mark_message_sent(
        queue_id=test_qid,
        message_id="wamid.TEST.CLEANUP",
        provider="baileys",
        delivery_status="accepted",
    )
    dead_qid = db.enqueue_message(
        phone="+917333333333",
        message="test dead",
        provider="baileys",
        source="test",
    )
    for _ in range(5):
        db.mark_message_failed(queue_id=dead_qid, error_message="forced")

    # Re-open DB object to trigger one-time startup cleanup path.
    MessageQueueDB(db_path=str(db_path))

    db_after = MessageQueueDB(db_path=str(db_path))
    pending = db_after.get_pending_messages(limit=50)
    history = db_after.get_message_history(limit=50)
    dead = db_after.get_dead_letter_messages(limit=50)

    assert any(row["id"] == keep_qid for row in pending)
    assert all(row.get("source") != "test" for row in pending)
    assert all(row.get("source") != "test" for row in history)
    assert all(row.get("source") != "test" for row in dead)
