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
from app.utils.phone import normalize_phone_e164

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
                    source TEXT DEFAULT 'api',
                    batch_id TEXT,
                    party_code TEXT
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
                    contact_name TEXT,
                    contact_source TEXT,
                    contact_is_saved INTEGER,
                    contact_state TEXT,
                    batch_id TEXT,
                    party_code TEXT,
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
                    batch_id TEXT,
                    party_code TEXT,
                    retry_count INTEGER,
                    final_error TEXT,
                    created_at TIMESTAMP,
                    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (queue_id) REFERENCES message_queue(id)
                )
            """)

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_batches (
                    batch_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    company_id TEXT DEFAULT 'default',
                    template_id TEXT,
                    sent_by TEXT DEFAULT 'manual',
                    total_parties INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'sending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    queue_success_count INTEGER DEFAULT 0,
                    queue_failed_count INTEGER DEFAULT 0,
                    skipped_count INTEGER DEFAULT 0,
                    delivery_accepted_count INTEGER DEFAULT 0,
                    delivery_sent_count INTEGER DEFAULT 0,
                    delivery_delivered_count INTEGER DEFAULT 0,
                    delivery_read_count INTEGER DEFAULT 0,
                    delivery_failed_count INTEGER DEFAULT 0,
                    in_flight_count INTEGER DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_batch_recipients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    party_code TEXT NOT NULL,
                    recipient_name TEXT,
                    phone TEXT,
                    queue_id INTEGER,
                    message_id TEXT,
                    status TEXT DEFAULT 'pending',
                    queue_status TEXT DEFAULT 'pending',
                    delivery_status TEXT DEFAULT 'unknown',
                    failure_stage TEXT,
                    failure_code TEXT,
                    failure_message TEXT,
                    contact_name TEXT,
                    contact_source TEXT,
                    contact_is_saved INTEGER DEFAULT 0,
                    contact_state TEXT,
                    retry_count INTEGER DEFAULT 0,
                    is_dead_letter INTEGER DEFAULT 0,
                    amount_due TEXT,
                    media_attached INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(batch_id, party_code),
                    FOREIGN KEY (batch_id) REFERENCES reminder_batches(batch_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
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
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminder_batch_created_at ON reminder_batches(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminder_recipient_batch_id ON reminder_batch_recipients(batch_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminder_recipient_party_code ON reminder_batch_recipients(party_code)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminder_recipient_status ON reminder_batch_recipients(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminder_recipient_failure_stage ON reminder_batch_recipients(failure_stage)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminder_recipient_created_at ON reminder_batch_recipients(created_at)
            """)
            
            conn.commit()
            self._run_migrations(conn)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_source ON message_history(source)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_batch_party ON message_queue(batch_id, party_code)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_batch_party ON message_history(batch_id, party_code)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dead_letter_batch_party ON dead_letter_queue(batch_id, party_code)
            """)
            conn.commit()
            self._cleanup_legacy_test_data(conn)
            logger.info("message_queue_db_initialized", db_path=str(self.db_path))

    def _get_app_state(self, conn: sqlite3.Connection, key: str) -> Optional[str]:
        row = conn.execute(
            "SELECT value FROM app_state WHERE key = ?",
            (key,),
        ).fetchone()
        if not row:
            return None
        return row["value"]

    def _set_app_state(self, conn: sqlite3.Connection, key: str, value: str) -> None:
        conn.execute(
            """
            INSERT INTO app_state (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )

    def _cleanup_legacy_test_data(self, conn: sqlite3.Connection) -> None:
        marker = "cleanup_test_source_v2_done"
        already_marked = self._get_app_state(conn, marker) == "1"
        queue_deleted = conn.execute(
            """
            DELETE FROM message_queue
            WHERE source = ?
               OR LOWER(COALESCE(pdf_url, '')) LIKE ?
               OR LOWER(COALESCE(pdf_url, '')) LIKE ?
               OR LOWER(COALESCE(pdf_url, '')) LIKE ?
            """,
            ("test", "%example.com/%", "%example.org/%", "%test-invoice%"),
        ).rowcount
        history_deleted = conn.execute(
            """
            DELETE FROM message_history
            WHERE source = ?
               OR LOWER(COALESCE(pdf_url, '')) LIKE ?
               OR LOWER(COALESCE(pdf_url, '')) LIKE ?
               OR LOWER(COALESCE(pdf_url, '')) LIKE ?
            """,
            ("test", "%example.com/%", "%example.org/%", "%test-invoice%"),
        ).rowcount
        dead_letter_deleted = conn.execute(
            """
            DELETE FROM dead_letter_queue
            WHERE source = ?
               OR LOWER(COALESCE(pdf_url, '')) LIKE ?
               OR LOWER(COALESCE(pdf_url, '')) LIKE ?
               OR LOWER(COALESCE(pdf_url, '')) LIKE ?
            """,
            ("test", "%example.com/%", "%example.org/%", "%test-invoice%"),
        ).rowcount
        if not already_marked:
            self._set_app_state(conn, marker, "1")
        conn.commit()
        if (queue_deleted + history_deleted + dead_letter_deleted) > 0 or not already_marked:
            logger.info(
                "legacy_test_data_cleanup_complete",
                queue_deleted=queue_deleted,
                history_deleted=history_deleted,
                dead_letter_deleted=dead_letter_deleted,
            )

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
        if not self._has_column(conn, "message_history", "contact_name"):
            conn.execute("ALTER TABLE message_history ADD COLUMN contact_name TEXT")
            migrated = True
        if not self._has_column(conn, "message_history", "contact_source"):
            conn.execute("ALTER TABLE message_history ADD COLUMN contact_source TEXT")
            migrated = True
        if not self._has_column(conn, "message_history", "contact_is_saved"):
            conn.execute("ALTER TABLE message_history ADD COLUMN contact_is_saved INTEGER")
            migrated = True
        if not self._has_column(conn, "message_history", "contact_state"):
            conn.execute("ALTER TABLE message_history ADD COLUMN contact_state TEXT")
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
        if not self._has_column(conn, "message_queue", "batch_id"):
            conn.execute("ALTER TABLE message_queue ADD COLUMN batch_id TEXT")
            migrated = True
        if not self._has_column(conn, "message_queue", "party_code"):
            conn.execute("ALTER TABLE message_queue ADD COLUMN party_code TEXT")
            migrated = True
        if not self._has_column(conn, "message_history", "batch_id"):
            conn.execute("ALTER TABLE message_history ADD COLUMN batch_id TEXT")
            migrated = True
        if not self._has_column(conn, "message_history", "party_code"):
            conn.execute("ALTER TABLE message_history ADD COLUMN party_code TEXT")
            migrated = True
        if not self._has_column(conn, "dead_letter_queue", "batch_id"):
            conn.execute("ALTER TABLE dead_letter_queue ADD COLUMN batch_id TEXT")
            migrated = True
        if not self._has_column(conn, "dead_letter_queue", "party_code"):
            conn.execute("ALTER TABLE dead_letter_queue ADD COLUMN party_code TEXT")
            migrated = True
        if not self._has_column(conn, "reminder_batch_recipients", "contact_name"):
            conn.execute("ALTER TABLE reminder_batch_recipients ADD COLUMN contact_name TEXT")
            migrated = True
        if not self._has_column(conn, "reminder_batch_recipients", "contact_source"):
            conn.execute("ALTER TABLE reminder_batch_recipients ADD COLUMN contact_source TEXT")
            migrated = True
        if not self._has_column(conn, "reminder_batch_recipients", "contact_is_saved"):
            conn.execute("ALTER TABLE reminder_batch_recipients ADD COLUMN contact_is_saved INTEGER DEFAULT 0")
            migrated = True
        if not self._has_column(conn, "reminder_batch_recipients", "contact_state"):
            conn.execute("ALTER TABLE reminder_batch_recipients ADD COLUMN contact_state TEXT")
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

    def create_reminder_batch(
        self,
        *,
        batch_id: str,
        session_id: Optional[str],
        company_id: str,
        template_id: str,
        sent_by: str,
        total_parties: int,
    ) -> None:
        """Create or replace reminder batch metadata row."""
        now = datetime.now()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reminder_batches
                (batch_id, session_id, company_id, template_id, sent_by, total_parties, status, created_at, started_at)
                VALUES (?, ?, ?, ?, ?, ?, 'sending', ?, ?)
                """,
                (batch_id, session_id, company_id, template_id, sent_by, total_parties, now, now),
            )
            conn.commit()

    def set_reminder_batch_status(self, batch_id: str, status: str) -> None:
        """Update reminder batch status and completion timestamp."""
        now = datetime.now()
        completed_at = now if status in ("completed", "failed", "cancelled", "stopped") else None
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE reminder_batches
                SET status = ?,
                    completed_at = COALESCE(?, completed_at)
                WHERE batch_id = ?
                """,
                (status, completed_at, batch_id),
            )
            self._refresh_reminder_batch_aggregates(conn, batch_id)
            conn.commit()

    def upsert_reminder_batch_recipient(
        self,
        *,
        batch_id: str,
        party_code: str,
        recipient_name: Optional[str] = None,
        phone: Optional[str] = None,
        queue_id: Optional[int] = None,
        message_id: Optional[str] = None,
        status: Optional[str] = None,
        queue_status: Optional[str] = None,
        delivery_status: Optional[str] = None,
        failure_stage: Optional[str] = None,
        failure_code: Optional[str] = None,
        failure_message: Optional[str] = None,
        contact_name: Optional[str] = None,
        contact_source: Optional[str] = None,
        contact_is_saved: Optional[bool] = None,
        contact_state: Optional[str] = None,
        retry_count: Optional[int] = None,
        is_dead_letter: Optional[bool] = None,
        amount_due: Optional[str] = None,
        media_attached: Optional[bool] = None,
    ) -> None:
        """Upsert per-recipient report row."""
        now = datetime.now()
        dead_letter = int(is_dead_letter) if is_dead_letter is not None else None
        media = int(media_attached) if media_attached is not None else None
        saved_flag = int(contact_is_saved) if contact_is_saved is not None else None
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reminder_batch_recipients
                (batch_id, party_code, recipient_name, phone, queue_id, message_id, status, queue_status, delivery_status,
                 failure_stage, failure_code, failure_message, contact_name, contact_source, contact_is_saved, contact_state,
                 retry_count, is_dead_letter, amount_due, media_attached,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, 0), ?, COALESCE(?, 0), ?, ?)
                ON CONFLICT(batch_id, party_code) DO UPDATE SET
                    recipient_name = COALESCE(excluded.recipient_name, reminder_batch_recipients.recipient_name),
                    phone = COALESCE(excluded.phone, reminder_batch_recipients.phone),
                    queue_id = COALESCE(excluded.queue_id, reminder_batch_recipients.queue_id),
                    message_id = COALESCE(excluded.message_id, reminder_batch_recipients.message_id),
                    status = COALESCE(excluded.status, reminder_batch_recipients.status),
                    queue_status = COALESCE(excluded.queue_status, reminder_batch_recipients.queue_status),
                    delivery_status = COALESCE(excluded.delivery_status, reminder_batch_recipients.delivery_status),
                    failure_stage = COALESCE(excluded.failure_stage, reminder_batch_recipients.failure_stage),
                    failure_code = COALESCE(excluded.failure_code, reminder_batch_recipients.failure_code),
                    failure_message = COALESCE(excluded.failure_message, reminder_batch_recipients.failure_message),
                    contact_name = COALESCE(excluded.contact_name, reminder_batch_recipients.contact_name),
                    contact_source = COALESCE(excluded.contact_source, reminder_batch_recipients.contact_source),
                    contact_is_saved = COALESCE(excluded.contact_is_saved, reminder_batch_recipients.contact_is_saved),
                    contact_state = COALESCE(excluded.contact_state, reminder_batch_recipients.contact_state),
                    retry_count = COALESCE(excluded.retry_count, reminder_batch_recipients.retry_count),
                    is_dead_letter = COALESCE(excluded.is_dead_letter, reminder_batch_recipients.is_dead_letter),
                    amount_due = COALESCE(excluded.amount_due, reminder_batch_recipients.amount_due),
                    media_attached = COALESCE(excluded.media_attached, reminder_batch_recipients.media_attached),
                    updated_at = excluded.updated_at
                """,
                (
                    batch_id,
                    party_code,
                    recipient_name,
                    phone,
                    queue_id,
                    message_id,
                    status,
                    queue_status,
                    delivery_status,
                    failure_stage,
                    failure_code,
                    failure_message,
                    contact_name,
                    contact_source,
                    saved_flag,
                    contact_state,
                    retry_count,
                    dead_letter,
                    amount_due,
                    media,
                    now,
                    now,
                ),
            )
            self._refresh_reminder_batch_aggregates(conn, batch_id)
            conn.commit()

    def _refresh_reminder_batch_aggregates(self, conn: sqlite3.Connection, batch_id: str) -> None:
        """Recompute aggregate counters for a batch."""
        cursor = conn.execute(
            """
            SELECT
                SUM(CASE WHEN queue_status = 'queued' THEN 1 ELSE 0 END) AS queue_success_count,
                SUM(CASE WHEN status = 'failed' AND queue_status != 'queued' THEN 1 ELSE 0 END) AS queue_failed_count,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) AS skipped_count,
                SUM(CASE WHEN delivery_status = 'accepted' THEN 1 ELSE 0 END) AS delivery_accepted_count,
                SUM(CASE WHEN delivery_status = 'sent' THEN 1 ELSE 0 END) AS delivery_sent_count,
                SUM(CASE WHEN delivery_status = 'delivered' THEN 1 ELSE 0 END) AS delivery_delivered_count,
                SUM(CASE WHEN delivery_status = 'read' THEN 1 ELSE 0 END) AS delivery_read_count,
                SUM(CASE WHEN delivery_status = 'failed' THEN 1 ELSE 0 END) AS delivery_failed_count,
                SUM(
                    CASE
                        WHEN queue_status = 'queued' AND delivery_status IN ('unknown', 'accepted', 'sent')
                        THEN 1
                        ELSE 0
                    END
                ) AS in_flight_count
            FROM reminder_batch_recipients
            WHERE batch_id = ?
            """,
            (batch_id,),
        )
        row = cursor.fetchone()
        conn.execute(
            """
            UPDATE reminder_batches
            SET queue_success_count = COALESCE(?, 0),
                queue_failed_count = COALESCE(?, 0),
                skipped_count = COALESCE(?, 0),
                delivery_accepted_count = COALESCE(?, 0),
                delivery_sent_count = COALESCE(?, 0),
                delivery_delivered_count = COALESCE(?, 0),
                delivery_read_count = COALESCE(?, 0),
                delivery_failed_count = COALESCE(?, 0),
                in_flight_count = COALESCE(?, 0)
            WHERE batch_id = ?
            """,
            (
                row["queue_success_count"] if row else 0,
                row["queue_failed_count"] if row else 0,
                row["skipped_count"] if row else 0,
                row["delivery_accepted_count"] if row else 0,
                row["delivery_sent_count"] if row else 0,
                row["delivery_delivered_count"] if row else 0,
                row["delivery_read_count"] if row else 0,
                row["delivery_failed_count"] if row else 0,
                row["in_flight_count"] if row else 0,
                batch_id,
            ),
        )

    def get_reminder_batch_report(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Return reminder batch report with summary and recipient rows."""
        with self._get_connection() as conn:
            self._refresh_reminder_batch_aggregates(conn, batch_id)
            batch_row = conn.execute(
                "SELECT * FROM reminder_batches WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
            if not batch_row:
                return None
            recipient_rows = conn.execute(
                """
                SELECT * FROM reminder_batch_recipients
                WHERE batch_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (batch_id,),
            ).fetchall()
            conn.commit()
            return {
                "batch": dict(batch_row),
                "recipients": [dict(r) for r in recipient_rows],
            }

    def get_reminder_batch_failures(
        self,
        batch_id: str,
        failure_stage: Optional[str] = None,
        failure_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return failed recipients for a batch with optional filters."""
        query = """
            SELECT * FROM reminder_batch_recipients
            WHERE batch_id = ? AND status = 'failed'
        """
        params: List[Any] = [batch_id]
        if failure_stage:
            query += " AND failure_stage = ?"
            params.append(failure_stage)
        if failure_code:
            query += " AND failure_code = ?"
            params.append(failure_code)
        query += " ORDER BY updated_at DESC, id DESC"
        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def list_recent_reminder_batches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent reminder batches."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM reminder_batches
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_batch_id_for_session(self, session_id: str) -> Optional[str]:
        """Find the latest batch ID associated with a session."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT batch_id
                FROM reminder_batches
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            return str(row["batch_id"]) if row else None

    def get_reminder_batch_company_id(self, batch_id: Optional[str]) -> str:
        """Resolve company id for a reminder batch."""
        if not batch_id:
            return "default"
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT company_id
                FROM reminder_batches
                WHERE batch_id = ?
                LIMIT 1
                """,
                (batch_id,),
            ).fetchone()
            return str((row["company_id"] if row else None) or "default")
    
    def enqueue_message(
        self,
        phone: str,
        message: str,
        pdf_url: Optional[str] = None,
        file_name: Optional[str] = None,
        provider: str = "baileys",
        source: str = "api",
        batch_id: Optional[str] = None,
        party_code: Optional[str] = None,
    ) -> int:
        """Add a message to the queue."""
        incoming_phone = (phone or "").strip()
        if not incoming_phone:
            logger.warning(
                "message_enqueue_validation_failed",
                reason="phone_empty",
                source=source,
                provider=provider,
                batch_id=batch_id,
                party_code=party_code,
            )
            raise ValueError("phone_validation_failed: phone is empty")
        try:
            normalized_phone = normalize_phone_e164(incoming_phone)
        except ValueError as exc:
            logger.warning(
                "message_enqueue_validation_failed",
                reason="phone_invalid",
                error=str(exc),
                phone=incoming_phone,
                source=source,
                provider=provider,
                batch_id=batch_id,
                party_code=party_code,
            )
            raise

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO message_queue 
                (phone, message, pdf_url, file_name, provider, status, source, next_retry_at, batch_id, party_code)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (
                    normalized_phone,
                    message,
                    pdf_url,
                    file_name,
                    provider,
                    source,
                    datetime.now(),
                    batch_id,
                    party_code,
                )
            )
            conn.commit()
            message_id = cursor.lastrowid
            logger.info(
                "message_enqueued",
                queue_id=message_id,
                phone=normalized_phone,
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
        delivery_status: str = "accepted",
        resolved_phone: Optional[str] = None,
        contact_name: Optional[str] = None,
        contact_source: Optional[str] = None,
        contact_is_saved: Optional[bool] = None,
        contact_state: Optional[str] = None,
    ):
        """Mark message as successfully sent and move to history."""
        now = datetime.now()
        normalized_delivery = (delivery_status or "accepted").strip().lower()
        if normalized_delivery not in {"accepted", "sent", "delivered", "read", "failed", "unknown"}:
            normalized_delivery = "accepted"
        
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
                     delivered_at, read_at, failed_at, recipient_waid, contact_name, contact_source, contact_is_saved, contact_state, batch_id, party_code,
                     created_at, sent_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        'sent',
                        row['retry_count'],
                        message_id,
                        normalized_delivery,
                        now,
                        (now if normalized_delivery == "delivered" else None),
                        (now if normalized_delivery == "read" else None),
                        (now if normalized_delivery == "failed" else None),
                        (resolved_phone.lstrip('+') if resolved_phone else None),
                        contact_name,
                        contact_source,
                        (int(contact_is_saved) if contact_is_saved is not None else None),
                        contact_state,
                        (row['batch_id'] if 'batch_id' in row.keys() else None),
                        (row['party_code'] if 'party_code' in row.keys() else None),
                        row['created_at'],
                        now,
                        now,
                    )
                )
                if (
                    row["source"] == "payment_reminder"
                    and row["batch_id"]
                    and row["party_code"]
                ):
                    mapped_status = "sent" if normalized_delivery != "failed" else "failed"
                    conn.execute(
                        """
                        UPDATE reminder_batch_recipients
                        SET message_id = ?,
                            phone = COALESCE(?, phone),
                            status = ?,
                            queue_status = 'queued',
                            delivery_status = ?,
                            contact_name = COALESCE(?, contact_name),
                            contact_source = COALESCE(?, contact_source),
                            contact_is_saved = COALESCE(?, contact_is_saved),
                            contact_state = COALESCE(?, contact_state),
                            failure_stage = CASE WHEN ? = 'failed' THEN 'provider_send' ELSE failure_stage END,
                            failure_code = CASE WHEN ? = 'failed' THEN COALESCE(failure_code, 'provider_send_failed') ELSE failure_code END,
                            failure_message = CASE WHEN ? = 'failed' THEN COALESCE(failure_message, 'Provider send returned failed status') ELSE failure_message END,
                            updated_at = ?
                        WHERE batch_id = ? AND party_code = ?
                        """,
                        (
                            message_id,
                            (resolved_phone or row["phone"]),
                            mapped_status,
                            normalized_delivery,
                            contact_name,
                            contact_source,
                            (int(contact_is_saved) if contact_is_saved is not None else None),
                            contact_state,
                            normalized_delivery,
                            normalized_delivery,
                            normalized_delivery,
                            now,
                            row["batch_id"],
                            row["party_code"],
                        ),
                    )
                    self._refresh_reminder_batch_aggregates(conn, row["batch_id"])
                
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
                    delivery_status=normalized_delivery,
                    phone=resolved_phone or row['phone'],
                )

    @staticmethod
    def _delivery_rank(status: str) -> int:
        order = {
            "unknown": 0,
            "accepted": 1,
            "sent": 2,
            "delivered": 3,
            "read": 4,
            "failed": 5,
        }
        return order.get((status or "unknown").strip().lower(), 0)
    
    def mark_message_failed(
        self,
        queue_id: int,
        error_message: str
    ):
        """Mark message as failed and schedule retry or move to dead letter."""
        now = datetime.now()
        lowered_error = (error_message or "").strip().lower()
        non_retryable_phone_error = any(
            token in lowered_error
            for token in (
                "phone_validation_failed",
                "phone is empty",
                "phone is required",
                "phone has no digits",
                "phone length invalid",
                "not a valid indian mobile",
            )
        )
        recoverable_bridge_error = any(
            token in lowered_error
            for token in (
                "bridge_session_degraded_retryable",
                "bad mac",
                "failed to decrypt",
                "not connected to whatsapp",
            )
        )
        
        with self._get_connection() as conn:
            # Get current retry count
            cursor = conn.execute(
                "SELECT retry_count, max_retries FROM message_queue WHERE id = ?",
                (queue_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return
            
            if non_retryable_phone_error:
                new_retry_count = row['max_retries']
            else:
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
                     final_error, created_at, failed_at, batch_id, party_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        queue_id, msg_row['phone'], msg_row['message'],
                        msg_row['pdf_url'], (msg_row['file_name'] if 'file_name' in msg_row.keys() else None),
                        msg_row['provider'], (msg_row['source'] if 'source' in msg_row.keys() else 'api'),
                        new_retry_count, error_message,
                        msg_row['created_at'], now,
                        (msg_row['batch_id'] if 'batch_id' in msg_row.keys() else None),
                        (msg_row['party_code'] if 'party_code' in msg_row.keys() else None),
                    )
                )
                if (
                    msg_row["source"] == "payment_reminder"
                    and msg_row["batch_id"]
                    and msg_row["party_code"]
                ):
                    failure_stage = "validation" if non_retryable_phone_error else "dead_letter"
                    failure_code = "invalid_phone" if non_retryable_phone_error else "retry_exhausted"
                    conn.execute(
                        """
                        UPDATE reminder_batch_recipients
                        SET status = 'failed',
                            queue_status = 'failed',
                            delivery_status = 'failed',
                            failure_stage = ?,
                            failure_code = ?,
                            failure_message = ?,
                            retry_count = ?,
                            is_dead_letter = 1,
                            updated_at = ?
                        WHERE batch_id = ? AND party_code = ?
                        """,
                        (
                            failure_stage,
                            failure_code,
                            error_message,
                            new_retry_count,
                            now,
                            msg_row["batch_id"],
                            msg_row["party_code"],
                        ),
                    )
                    self._refresh_reminder_batch_aggregates(conn, msg_row["batch_id"])
                
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
                    error=error_message,
                    non_retryable=non_retryable_phone_error,
                )
            else:
                # Schedule retry with exponential backoff
                # Retry delays: immediate, 30s, 5min, 15min, 1hr
                delays = [0, 30, 300, 900, 3600]
                if recoverable_bridge_error:
                    delay = 5 if new_retry_count <= 2 else 30
                else:
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
                msg_row = conn.execute(
                    "SELECT source, batch_id, party_code FROM message_queue WHERE id = ?",
                    (queue_id,),
                ).fetchone()
                if (
                    msg_row
                    and msg_row["source"] == "payment_reminder"
                    and msg_row["batch_id"]
                    and msg_row["party_code"]
                ):
                    conn.execute(
                        """
                        UPDATE reminder_batch_recipients
                        SET status = 'failed',
                            queue_status = 'retrying',
                            failure_stage = 'provider_send',
                            failure_code = 'provider_send_failed',
                            failure_message = ?,
                            retry_count = ?,
                            updated_at = ?
                        WHERE batch_id = ? AND party_code = ?
                        """,
                        (error_message, new_retry_count, now, msg_row["batch_id"], msg_row["party_code"]),
                    )
                    self._refresh_reminder_batch_aggregates(conn, msg_row["batch_id"])
                
                conn.commit()
                logger.info(
                    "message_retry_scheduled",
                    queue_id=queue_id,
                    retry_count=new_retry_count,
                    next_retry=next_retry.isoformat(),
                    delay_seconds=delay,
                    recoverable_bridge_error=recoverable_bridge_error,
                )

    def defer_message(
        self,
        queue_id: int,
        *,
        delay_seconds: int,
        reason: str,
    ) -> None:
        """Defer a queued message without consuming a retry attempt."""
        now = datetime.now()
        next_retry = now + timedelta(seconds=max(1, int(delay_seconds)))

        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT source, batch_id, party_code FROM message_queue WHERE id = ?",
                (queue_id,),
            ).fetchone()
            if not row:
                return

            conn.execute(
                """
                UPDATE message_queue
                SET status = 'retrying',
                    error_message = ?,
                    next_retry_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (reason, next_retry, now, queue_id),
            )

            if (
                row["source"] == "payment_reminder"
                and row["batch_id"]
                and row["party_code"]
            ):
                conn.execute(
                    """
                    UPDATE reminder_batch_recipients
                    SET status = 'held',
                        queue_status = 'retrying',
                        failure_stage = 'dispatch_hold',
                        failure_code = 'dispatch_held',
                        failure_message = ?,
                        updated_at = ?
                    WHERE batch_id = ? AND party_code = ?
                    """,
                    (reason, now, row["batch_id"], row["party_code"]),
                )
                self._refresh_reminder_batch_aggregates(conn, row["batch_id"])

            conn.commit()
            logger.info(
                "message_deferred",
                queue_id=queue_id,
                delay_seconds=delay_seconds,
                next_retry=next_retry.isoformat(),
                reason=reason,
            )

    def update_delivery_status(
        self,
        message_id: str,
        delivery_status: str,
        error_message: Optional[str] = None,
        recipient_waid: Optional[str] = None,
        contact_name: Optional[str] = None,
        contact_source: Optional[str] = None,
        contact_is_saved: Optional[bool] = None,
        contact_state: Optional[str] = None,
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
        if normalized not in {"accepted", "sent", "delivered", "read", "failed", "unknown"}:
            normalized = "unknown"

        final_status = "failed" if normalized == "failed" else "sent"
        payload_text = json.dumps(raw_payload, ensure_ascii=False) if raw_payload else None
        delivered_at = now if normalized == "delivered" else None
        read_at = now if normalized == "read" else None
        failed_at = now if normalized == "failed" else None

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, delivery_status FROM message_history WHERE message_id = ? ORDER BY id DESC LIMIT 1",
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
            current_delivery = (row["delivery_status"] or "unknown").strip().lower()
            # Monotonic lifecycle updates:
            # accepted -> sent -> delivered -> read
            # failed is terminal unless existing state is read (do not regress from read).
            if current_delivery == "read" and normalized != "read":
                logger.info(
                    "delivery_status_update_ignored",
                    message_id=message_id,
                    current_status=current_delivery,
                    incoming_status=normalized,
                    reason="current_read_terminal",
                )
                return True
            if normalized != "failed" and self._delivery_rank(normalized) < self._delivery_rank(current_delivery):
                logger.info(
                    "delivery_status_update_ignored",
                    message_id=message_id,
                    current_status=current_delivery,
                    incoming_status=normalized,
                    reason="non_monotonic",
                )
                return True
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
                    contact_name = COALESCE(?, contact_name),
                    contact_source = COALESCE(?, contact_source),
                    contact_is_saved = COALESCE(?, contact_is_saved),
                    contact_state = COALESCE(?, contact_state),
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
                    contact_name,
                    contact_source,
                    (int(contact_is_saved) if contact_is_saved is not None else None),
                    contact_state,
                    provider,
                    current_error,
                    current_error,
                    now,
                    history_id,
                ),
            )
            history_row = conn.execute(
                "SELECT batch_id, party_code FROM message_history WHERE id = ?",
                (history_id,),
            ).fetchone()
            if (
                history_row
                and history_row["batch_id"]
                and history_row["party_code"]
            ):
                failure_stage = "delivery_webhook" if normalized == "failed" else None
                failure_code = "delivery_failed" if normalized == "failed" else None
                conn.execute(
                    """
                    UPDATE reminder_batch_recipients
                    SET status = ?,
                        delivery_status = ?,
                        failure_stage = COALESCE(?, failure_stage),
                        failure_code = COALESCE(?, failure_code),
                        contact_name = COALESCE(?, contact_name),
                        contact_source = COALESCE(?, contact_source),
                        contact_is_saved = COALESCE(?, contact_is_saved),
                        contact_state = COALESCE(?, contact_state),
                        failure_message = CASE
                            WHEN ? IS NOT NULL THEN ?
                            ELSE failure_message
                        END,
                        message_id = COALESCE(?, message_id),
                        updated_at = ?
                    WHERE batch_id = ? AND party_code = ?
                    """,
                    (
                        final_status,
                        normalized,
                        failure_stage,
                        failure_code,
                        contact_name,
                        contact_source,
                        (int(contact_is_saved) if contact_is_saved is not None else None),
                        contact_state,
                        current_error,
                        current_error,
                        message_id,
                        now,
                        history_row["batch_id"],
                        history_row["party_code"],
                    ),
                )
                self._refresh_reminder_batch_aggregates(conn, history_row["batch_id"])
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

    def count_message_history(
        self,
        phone: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        delivery_status: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> int:
        """Count message history rows for pagination metadata."""
        query = "SELECT COUNT(*) AS total FROM message_history WHERE 1=1"
        params: List[Any] = []
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
        if from_time:
            query += " AND completed_at >= ?"
            params.append(from_time)
        if to_time:
            query += " AND completed_at <= ?"
            params.append(to_time)
        with self._get_connection() as conn:
            row = conn.execute(query, params).fetchone()
            return int(row["total"] if row else 0)

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
                 next_retry_at, created_at, updated_at, source, batch_id, party_code)
                VALUES (?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row['phone'], row['message'], row['pdf_url'], (row['file_name'] if 'file_name' in row.keys() else None),
                    row['provider'], datetime.now(),
                    row['created_at'], datetime.now(), (row['source'] if 'source' in row.keys() else 'api'),
                    (row['batch_id'] if 'batch_id' in row.keys() else None),
                    (row['party_code'] if 'party_code' in row.keys() else None),
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
