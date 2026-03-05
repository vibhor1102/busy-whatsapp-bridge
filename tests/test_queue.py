#!/usr/bin/env python3
"""
Test script for message queue system.
Tests enqueue, processing, retry logic, and history tracking.
"""

import os
from pathlib import Path

from app.database.message_queue import MessageQueueDB


def test_queue_operations(tmp_path: Path):
    """Test basic queue operations."""
    message_db = MessageQueueDB(db_path=str(tmp_path / "messages.db"))

    print("=" * 60)
    print("Testing Message Queue System")
    print("=" * 60)
    print()
    
    # Test 1: Enqueue messages
    print("Test 1: Enqueue messages")
    print("-" * 40)
    
    msg1_id = message_db.enqueue_message(
        phone="+919876543210",
        message="Test invoice message 1",
        pdf_url="https://example.com/invoice1.pdf",
        provider="baileys",
        source="test"
    )
    print(f"[OK] Enqueued message 1: ID={msg1_id}")
    
    msg2_id = message_db.enqueue_message(
        phone="+919876543211",
        message="Test invoice message 2 (no PDF)",
        pdf_url=None,
        provider="baileys",
        source="test"
    )
    print(f"[OK] Enqueued message 2: ID={msg2_id}")
    
    msg3_id = message_db.enqueue_message(
        phone="+919876543212",
        message="Test message 3",
        provider="baileys",
        source="test"
    )
    print(f"[OK] Enqueued message 3: ID={msg3_id}")
    print()
    
    # Test 2: Get pending messages
    print("Test 2: Get pending messages")
    print("-" * 40)
    pending = message_db.get_pending_messages(limit=10)
    print(f"[OK] Found {len(pending)} pending messages")
    for msg in pending:
        print(f"  - ID {msg['id']}: {msg['phone']} - {msg['status']}")
    print()
    
    # Test 3: Mark one as sent
    print("Test 3: Mark message as sent")
    print("-" * 40)
    message_db.mark_message_sent(
        queue_id=msg1_id,
        message_id="test_msg_id_12345",
        provider="baileys"
    )
    print(f"[OK] Marked message {msg1_id} as sent")
    print()
    
    # Test 4: Mark one as failed (should trigger retry)
    print("Test 4: Mark message as failed (retry)")
    print("-" * 40)
    message_db.mark_message_failed(
        queue_id=msg2_id,
        error_message="Network timeout"
    )
    print(f"[OK] Marked message {msg2_id} as failed (will retry)")
    
    # Check retry status
    msg2 = message_db.get_message_by_id(msg2_id)
    print(f"  - Status: {msg2['status']}")
    print(f"  - Retry count: {msg2['retry_count']}")
    print(f"  - Next retry: {msg2['next_retry_at']}")
    print()
    
    # Test 5: Check queue stats
    print("Test 5: Queue statistics")
    print("-" * 40)
    stats = message_db.get_queue_stats()
    print(f"[OK] Pending: {stats['pending']}")
    print(f"[OK] Retrying: {stats['retrying']}")
    print(f"[OK] Dead letter: {stats['dead_letter']}")
    print(f"[OK] Sent today: {stats['sent_today']}")
    print(f"[OK] Total sent: {stats['total_sent']}")
    print(f"[OK] Total failed: {stats['total_failed']}")
    print()
    
    # Test 6: Get message history
    print("Test 6: Message history")
    print("-" * 40)
    history = message_db.get_message_history(limit=10)
    print(f"[OK] Found {len(history)} messages in history")
    for msg in history:
        print(f"  - ID {msg['queue_id']}: {msg['phone']} - {msg['status']}")
    print()
    
    # Test 7: Force dead letter
    print("Test 7: Force message to dead letter (5 failures)")
    print("-" * 40)
    
    # Simulate 5 failures for msg3
    for i in range(5):
        # Reset to pending first
        with message_db._get_connection() as conn:
            conn.execute(
                "UPDATE message_queue SET status = 'pending', retry_count = ? WHERE id = ?",
                (i, msg3_id)
            )
            conn.commit()
        
        # Mark as failed
        message_db.mark_message_failed(
            queue_id=msg3_id,
            error_message=f"Attempt {i+1} failed"
        )
        print(f"  - Failure {i+1}")
    
    print(f"[OK] Message {msg3_id} should now be in dead letter queue")
    
    dead_letters = message_db.get_dead_letter_messages(limit=10)
    print(f"[OK] Dead letter queue has {len(dead_letters)} messages")
    if dead_letters:
        print(f"  - Latest: ID {dead_letters[0]['queue_id']}, failed {dead_letters[0]['retry_count']} times")
    print()
    
    # Test 8: Retry from dead letter
    print("Test 8: Retry dead letter message")
    print("-" * 40)
    if dead_letters:
        dl_id = dead_letters[0]['id']
        success = message_db.retry_dead_letter(dl_id)
        print(f"[OK] Retry dead letter ID {dl_id}: {'Success' if success else 'Failed'}")
        
        # Verify it's back in queue
        pending_after = message_db.get_pending_messages(limit=10)
        print(f"[OK] Pending messages after retry: {len(pending_after)}")
    print()
    
    # Final stats
    print("=" * 60)
    print("Final Queue Statistics")
    print("=" * 60)
    final_stats = message_db.get_queue_stats()
    for key, value in final_stats.items():
        print(f"  {key}: {value}")
    print()
    print("All tests completed!")
    print()


if __name__ == "__main__":
    if os.environ.get("ALLOW_LIVE_QUEUE_TESTS", "").strip() != "1":
        raise SystemExit(
            "Refusing direct execution by default. "
            "Use pytest (isolated tmp DB) or set ALLOW_LIVE_QUEUE_TESTS=1 for manual run."
        )
    # Explicit opt-in manual run still uses a local DB file in repo root.
    test_queue_operations(Path("."))
