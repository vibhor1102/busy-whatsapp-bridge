"""
SQLite database for message queue and history.
Stores pending messages, retry attempts, and sent message history.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()


def _get_default_db_path() -> Path:
    """Get the default database path in Local AppData (machine-specific)."""
    from app.config import get_roaming_appdata_path
    appdata = get_roaming_appdata_path()
    data_dir = appdata / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "messages.db"


class MessageQueueDB:
    """SQLite database for message queue and history."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            self.db_path = _get_default_db_path()
        else:
            self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            # Message queue table (pending and retrying messages)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT NOT NULL,
                    message TEXT NOT NULL,
                    pdf_url TEXT,
                    file_name TEXT,
                    provider TEXT DEFAULT 'baileys',
                    status TEXT DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 5,
                    next_retry_at TIMESTAMP,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    message_id TEXT,
                    source TEXT DEFAULT 'api'
                )
            """)
            
            # Message history table (completed/failed messages)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_id INTEGER,
                    phone TEXT NOT NULL,
                    message TEXT NOT NULL,
                    pdf_url TEXT,
                    file_name TEXT,
                    provider TEXT,
                    source TEXT DEFAULT 'api',
                    status TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    message_id TEXT,
                    delivery_status TEXT DEFAULT 'unknown',
                    delivery_updated_at TIMESTAMP,
                    delivered_at TIMESTAMP,
                    read_at TIMESTAMP,
                    failed_at TIMESTAMP,
                    recipient_waid TEXT,
                    created_at TIMESTAMP,
                    sent_at TIMESTAMP,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (queue_id) REFERENCES message_queue(id)
                )
            """)

            # REMOVED: Meta webhook diagnostics tables (meta_webhook_diagnostics, meta_webhook_errors)
            # These were used for Meta Cloud API which has been removed.
            # TODO: Re-add via Baileys integration when needed
            
            # Dead letter queue (permanently failed messages)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dead_letter_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_id INTEGER,
                    phone TEXT NOT NULL,
                    message TEXT NOT NULL,
                    pdf_url TEXT,
                    file_name TEXT,
                    provider TEXT,
                    source TEXT DEFAULT 'api',
                    retry_count INTEGER,
                    final_error TEXT,
                    created_at TIMESTAMP,
                    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (queue_id) REFERENCES message_queue(id)
                )
            """)
            
            # Indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_status ON message_queue(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_retry ON message_queue(next_retry_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_phone ON message_history(phone)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_date ON message_history(completed_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_message_id ON message_history(message_id)
            """)
            
            conn.commit()
            self._run_migrations(conn)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_source ON message_history(source)
            """)
            conn.commit()
            logger.info("message_queue_db_initialized", db_path=str(self.db_path))

    def _has_column(self, conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
        """Check whether a table has the requested column."""
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = [row["name"] for row in cursor.fetchall()]
        return column_name in columns

    def _run_migrations(self, conn: sqlite3.Connection):
        """Apply lightweight schema migrations for existing databases."""
        migrated = False
        if not self._has_column(conn, "message_history", "source"):
            conn.execute("ALTER TABLE message_history ADD COLUMN source TEXT DEFAULT 'api'")
            migrated = True
        if not self._has_column(conn, "message_history", "delivery_status"):
            conn.execute("ALTER TABLE message_history ADD COLUMN delivery_status TEXT DEFAULT 'unknown'")
            migrated = True
        if not self._has_column(conn, "message_history", "delivery_updated_at"):
            conn.execute("ALTER TABLE message_history ADD COLUMN delivery_updated_at TIMESTAMP")
            migrated = True
        if not self._has_column(conn, "message_history", "delivered_at"):
            conn.execute("ALTER TABLE message_history ADD COLUMN delivered_at TIMESTAMP")
            migrated = True
        if not self._has_column(conn, "message_history", "read_at"):
            conn.execute("ALTER TABLE message_history ADD COLUMN read_at TIMESTAMP")
            migrated = True
        if not self._has_column(conn, "message_history", "failed_at"):
            conn.execute("ALTER TABLE message_history ADD COLUMN failed_at TIMESTAMP")
            migrated = True
        if not self._has_column(conn, "message_history", "recipient_waid"):
            conn.execute("ALTER TABLE message_history ADD COLUMN recipient_waid TEXT")
            migrated = True
        if not self._has_column(conn, "dead_letter_queue", "source"):
            conn.execute("ALTER TABLE dead_letter_queue ADD COLUMN source TEXT DEFAULT 'api'")
            migrated = True
        if not self._has_column(conn, "message_queue", "file_name"):
            conn.execute("ALTER TABLE message_queue ADD COLUMN file_name TEXT")
            migrated = True
        if not self._has_column(conn, "message_history", "file_name"):
            conn.execute("ALTER TABLE message_history ADD COLUMN file_name TEXT")
            migrated = True
        if not self._has_column(conn, "dead_letter_queue", "file_name"):
            conn.execute("ALTER TABLE dead_letter_queue ADD COLUMN file_name TEXT")
            migrated = True
        if migrated:
            conn.commit()
            logger.info("message_queue_db_migrated")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def enqueue_message(
        self,
        phone: str,
        message: str,
        pdf_url: Optional[str] = None,
        file_name: Optional[str] = None,
        provider: str = "baileys",
        source: str = "api"
    ) -> int:
        """Add a message to the queue."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO message_queue 
                (phone, message, pdf_url, file_name, provider, status, source, next_retry_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (phone, message, pdf_url, file_name, provider, source, datetime.now())
            )
            conn.commit()
            message_id = cursor.lastrowid
            logger.info(
                "message_enqueued",
                queue_id=message_id,
                phone=phone,
                provider=provider,
                source=source
            )
            return message_id
    
    def get_pending_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages ready to be processed (pending and due for retry)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM message_queue 
                WHERE status IN ('pending', 'retrying')
                AND (next_retry_at IS NULL OR next_retry_at <= ?)
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (datetime.now(), limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def mark_message_sent(
        self,
        queue_id: int,
        message_id: str,
        provider: str,
        delivery_status: str = "delivered",
        resolved_phone: Optional[str] = None,
    ):
        """Mark message as successfully sent and move to history."""
        now = datetime.now()
        
        with self._get_connection() as conn:
            # Get message data
            cursor = conn.execute(
                "SELECT * FROM message_queue WHERE id = ?",
                (queue_id,)
            )
            row = cursor.fetchone()
            
            if row:
                # Move to history
                conn.execute(
                    """
                    INSERT INTO message_history 
                    (queue_id, phone, message, pdf_url, file_name, provider, source, status, 
                     retry_count, message_id, delivery_status, delivery_updated_at,
                     delivered_at, read_at, failed_at, recipient_waid,
                     created_at, sent_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'sent', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        # sqlite3.Row behaves like a mapping but has no .get()
                        # method, so use key checks explicitly.
                        queue_id,
                        (resolved_phone or row['phone']),
                        row['message'],
                        row['pdf_url'],
                        row['file_name'] if 'file_name' in row.keys() else None,
                        provider,
                        (row['source'] if 'source' in row.keys() else 'api'),
                        row['retry_count'],
                        message_id,
                        delivery_status,
                        now,
                        (now if (delivery_status or "").strip().lower() == "delivered" else None),
                        (now if (delivery_status or "").strip().lower() == "read" else None),
                        (now if (delivery_status or "").strip().lower() == "failed" else None),
                        (resolved_phone.lstrip('+') if resolved_phone else None),
                        row['created_at'],
                        now,
                        now,
                    )
                )
                
                # Remove from queue
                conn.execute(
                    "DELETE FROM message_queue WHERE id = ?",
                    (queue_id,)
                )
                
                conn.commit()
                logger.info(
                    "message_sent_success",
                    queue_id=queue_id,
                    message_id=message_id,
                    provider=provider,
                    delivery_status=delivery_status,
                    phone=resolved_phone or row['phone'],
                )
    
    def mark_message_failed(
        self,
        queue_id: int,
        error_message: str
    ):
        """Mark message as failed and schedule retry or move to dead letter."""
        now = datetime.now()
        
        with self._get_connection() as conn:
            # Get current retry count
            cursor = conn.execute(
                "SELECT retry_count, max_retries FROM message_queue WHERE id = ?",
                (queue_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return
            
            new_retry_count = row['retry_count'] + 1
            
            if new_retry_count >= row['max_retries']:
                # Move to dead letter queue
                cursor = conn.execute(
                    "SELECT * FROM message_queue WHERE id = ?",
                    (queue_id,)
                )
                msg_row = cursor.fetchone()
                
                conn.execute(
                    """
                    INSERT INTO dead_letter_queue 
                    (queue_id, phone, message, pdf_url, file_name, provider, source, retry_count, 
                     final_error, created_at, failed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        queue_id, msg_row['phone'], msg_row['message'],
                        msg_row['pdf_url'], (msg_row['file_name'] if 'file_name' in msg_row.keys() else None),
                        msg_row['provider'], (msg_row['source'] if 'source' in msg_row.keys() else 'api'),
                        new_retry_count, error_message,
                        msg_row['created_at'], now
                    )
                )
                
                # Remove from queue
                conn.execute(
                    "DELETE FROM message_queue WHERE id = ?",
                    (queue_id,)
                )
                
                conn.commit()
                logger.warning(
                    "message_dead_letter",
                    queue_id=queue_id,
                    retry_count=new_retry_count,
                    error=error_message
                )
            else:
                # Schedule retry with exponential backoff
                # Retry delays: immediate, 30s, 5min, 15min, 1hr
                delays = [0, 30, 300, 900, 3600]
                delay = delays[min(new_retry_count, len(delays) - 1)]
                next_retry = now + timedelta(seconds=delay)
                
                conn.execute(
                    """
                    UPDATE message_queue 
                    SET status = 'retrying',
                        retry_count = ?,
                        error_message = ?,
                        next_retry_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (new_retry_count, error_message, next_retry, now, queue_id)
                )
                
                conn.commit()
                logger.info(
                    "message_retry_scheduled",
                    queue_id=queue_id,
                    retry_count=new_retry_count,
                    next_retry=next_retry.isoformat(),
                    delay_seconds=delay
                )

    def update_delivery_status(
        self,
        message_id: str,
        delivery_status: str,
        error_message: Optional[str] = None,
        recipient_waid: Optional[str] = None,
        provider: Optional[str] = None,
        event_time: Optional[datetime] = None,
        raw_payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update delivery lifecycle status for a previously accepted message.

        Returns True if a matching history record was found and updated.
        """
        if not message_id:
            return False

        now = event_time or datetime.now()
        normalized = (delivery_status or "").strip().lower()
        if not normalized:
            normalized = "unknown"

        final_status = "failed" if normalized == "failed" else "sent"
        payload_text = json.dumps(raw_payload, ensure_ascii=False) if raw_payload else None
        delivered_at = now if normalized == "delivered" else None
        read_at = now if normalized == "read" else None
        failed_at = now if normalized == "failed" else None

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM message_history WHERE message_id = ? ORDER BY id DESC LIMIT 1",
                (message_id,),
            )
            row = cursor.fetchone()
            if not row:
                logger.warning(
                    "delivery_status_message_not_found",
                    message_id=message_id,
                    delivery_status=normalized,
                )
                return False

            history_id = row["id"]
            current_error = error_message
            if payload_text:
                if current_error:
                    current_error = f"{current_error} | payload={payload_text}"
                else:
                    current_error = f"payload={payload_text}"

            conn.execute(
                """
                UPDATE message_history
                SET status = ?,
                    delivery_status = ?,
                    delivery_updated_at = ?,
                    delivered_at = COALESCE(?, delivered_at),
                    read_at = COALESCE(?, read_at),
                    failed_at = COALESCE(?, failed_at),
                    recipient_waid = COALESCE(?, recipient_waid),
                    provider = COALESCE(?, provider),
                    error_message = CASE
                        WHEN ? IS NOT NULL THEN ?
                        ELSE error_message
                    END,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    final_status,
                    normalized,
                    now,
                    delivered_at,
                    read_at,
                    failed_at,
                    recipient_waid,
                    provider,
                    current_error,
                    current_error,
                    now,
                    history_id,
                ),
            )
            conn.commit()

            logger.info(
                "delivery_status_updated",
                message_id=message_id,
                delivery_status=normalized,
                status=final_status,
                history_id=history_id,
            )
            return True
    
    def get_message_history(
        self,
        phone: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        delivery_status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query message history with filters."""
        query = "SELECT * FROM message_history WHERE 1=1"
        params = []
        
        if phone:
            query += " AND phone LIKE ?"
            params.append(f"%{phone}%")
        
        if status:
            query += " AND status = ?"
            params.append(status)

        if source:
            query += " AND source = ?"
            params.append(source)

        if delivery_status:
            query += " AND delivery_status = ?"
            params.append(delivery_status)
        
        if start_date:
            query += " AND completed_at >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND completed_at <= ?"
            params.append(end_date)

        if from_time:
            query += " AND completed_at >= ?"
            params.append(from_time)

        if to_time:
            query += " AND completed_at <= ?"
            params.append(to_time)
        
        query += " ORDER BY completed_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            normalized_rows: List[Dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                if not item.get("delivery_status"):
                    item["delivery_status"] = "unknown"
                normalized_rows.append(item)
            return normalized_rows

    # REMOVED: Meta webhook methods - Meta Cloud API removed
    # These methods were used for Meta webhook processing
    # TODO: Re-add via Baileys integration when needed
    # def record_meta_webhook_verify(...)
    # def record_meta_webhook_post(...)
    # def record_meta_webhook_error(...)
    # def get_meta_webhook_status(...)
    
    def get_dead_letter_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages from dead letter queue."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM dead_letter_queue 
                ORDER BY failed_at DESC 
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def retry_dead_letter(self, dead_letter_id: int) -> bool:
        """Move a message from dead letter queue back to active queue."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM dead_letter_queue WHERE id = ?",
                (dead_letter_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return False
            
            # Re-queue the message
            conn.execute(
                """
                INSERT INTO message_queue 
                (phone, message, pdf_url, file_name, provider, status, retry_count, 
                 next_retry_at, created_at, updated_at, source)
                VALUES (?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?, ?)
                """,
                (
                    row['phone'], row['message'], row['pdf_url'], (row['file_name'] if 'file_name' in row.keys() else None),
                    row['provider'], datetime.now(),
                    row['created_at'], datetime.now(), (row['source'] if 'source' in row.keys() else 'api')
                )
            )
            
            # Remove from dead letter
            conn.execute(
                "DELETE FROM dead_letter_queue WHERE id = ?",
                (dead_letter_id,)
            )
            
            conn.commit()
            logger.info(
                "dead_letter_retried",
                dead_letter_id=dead_letter_id,
                phone=row['phone']
            )
            return True
    
    def get_message_counts(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> Dict[str, int]:
        """Get message counts with filters using SQL aggregation.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            status: Optional status filter ('sent' or 'failed')
            
        Returns:
            Dict with legacy and delivery lifecycle counts
        """
        query = "SELECT status, delivery_status, COUNT(*) as count FROM message_history WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND completed_at >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND completed_at <= ?"
            params.append(end_date)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " GROUP BY status, delivery_status"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            counts = {
                "sent": 0,
                "failed": 0,
                "accepted": 0,
                "network_sent": 0,
                "delivered": 0,
                "read": 0,
            }
            for row in rows:
                row_status = (row["status"] or "").lower()
                delivery = (row["delivery_status"] or "").lower()
                count = int(row["count"])

                if row_status == "failed":
                    counts["failed"] += count
                    continue

                # Legacy "sent" should continue to represent successful sends.
                counts["sent"] += count
                if delivery == "accepted":
                    counts["accepted"] += count
                elif delivery == "sent":
                    counts["network_sent"] += count
                elif delivery == "delivered":
                    counts["delivered"] += count
                elif delivery == "read":
                    counts["read"] += count
            return counts

    def get_message_counts_by_source(
        self,
        source: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> Dict[str, int]:
        """Get sent/failed counts from history for a specific source."""
        query = "SELECT status, delivery_status, COUNT(*) as count FROM message_history WHERE source = ?"
        params: List[Any] = [source]

        if start_date:
            query += " AND completed_at >= ?"
            params.append(start_date)

        if end_date:
            query += " AND completed_at <= ?"
            params.append(end_date)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " GROUP BY status, delivery_status"

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            counts = {
                "sent": 0,
                "failed": 0,
                "accepted": 0,
                "network_sent": 0,
                "delivered": 0,
                "read": 0,
            }
            for row in rows:
                row_status = (row["status"] or "").lower()
                delivery = (row["delivery_status"] or "").lower()
                count = int(row["count"])

                if row_status == "failed":
                    counts["failed"] += count
                    continue

                counts["sent"] += count
                if delivery == "accepted":
                    counts["accepted"] += count
                elif delivery == "sent":
                    counts["network_sent"] += count
                elif delivery == "delivered":
                    counts["delivered"] += count
                elif delivery == "read":
                    counts["read"] += count
            return counts
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the queue."""
        with self._get_connection() as conn:
            # Pending messages
            cursor = conn.execute(
                "SELECT COUNT(*) FROM message_queue WHERE status = 'pending'"
            )
            pending = cursor.fetchone()[0]
            
            # Retrying messages
            cursor = conn.execute(
                "SELECT COUNT(*) FROM message_queue WHERE status = 'retrying'"
            )
            retrying = cursor.fetchone()[0]
            
            # Dead letter count
            cursor = conn.execute(
                "SELECT COUNT(*) FROM dead_letter_queue"
            )
            dead_letter = cursor.fetchone()[0]
            
            # Today's sent
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cursor = conn.execute(
                "SELECT COUNT(*) FROM message_history WHERE completed_at >= ? AND status = 'sent'",
                (today,)
            )
            sent_today = cursor.fetchone()[0]
            
            # Total sent
            cursor = conn.execute(
                "SELECT COUNT(*) FROM message_history WHERE status = 'sent'"
            )
            total_sent = cursor.fetchone()[0]
            
            # Total failed
            cursor = conn.execute(
                "SELECT COUNT(*) FROM message_history WHERE status = 'failed'"
            )
            total_failed = cursor.fetchone()[0]
            
            return {
                "pending": pending,
                "retrying": retrying,
                "dead_letter": dead_letter,
                "sent_today": sent_today,
                "total_sent": total_sent,
                "total_failed": total_failed
            }
    
    def get_message_by_id(self, queue_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific message from queue."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM message_queue WHERE id = ?",
                (queue_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def prune_history(self, days: int = 90) -> int:
        """Remove message history records older than specified days.
        
        Args:
            days: Number of days to keep history for.
            
        Returns:
            Number of records removed.
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM message_history WHERE completed_at < ?",
                (cutoff_date,)
            )
            count = cursor.rowcount
            conn.commit()
            
            if count > 0:
                logger.info("history_pruned", records_removed=count, days_kept=days, cutoff=cutoff_date)
            return count


# Global instance
message_db = MessageQueueDB()
