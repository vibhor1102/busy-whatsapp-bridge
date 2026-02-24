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
    """Get the default database path in AppData."""
    from app.config import get_appdata_path
    appdata = get_appdata_path()
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
                    provider TEXT,
                    status TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    message_id TEXT,
                    created_at TIMESTAMP,
                    sent_at TIMESTAMP,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (queue_id) REFERENCES message_queue(id)
                )
            """)
            
            # Dead letter queue (permanently failed messages)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dead_letter_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_id INTEGER,
                    phone TEXT NOT NULL,
                    message TEXT NOT NULL,
                    pdf_url TEXT,
                    provider TEXT,
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
            
            conn.commit()
            logger.info("message_queue_db_initialized", db_path=str(self.db_path))
    
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
        provider: str = "baileys",
        source: str = "api"
    ) -> int:
        """Add a message to the queue."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO message_queue 
                (phone, message, pdf_url, provider, status, source, next_retry_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (phone, message, pdf_url, provider, source, datetime.now())
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
        provider: str
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
                    (queue_id, phone, message, pdf_url, provider, status, 
                     retry_count, message_id, created_at, sent_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, 'sent', ?, ?, ?, ?, ?)
                    """,
                    (
                        queue_id, row['phone'], row['message'], row['pdf_url'],
                        provider, row['retry_count'], message_id,
                        row['created_at'], now, now
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
                    provider=provider
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
                    (queue_id, phone, message, pdf_url, provider, retry_count, 
                     final_error, created_at, failed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        queue_id, msg_row['phone'], msg_row['message'],
                        msg_row['pdf_url'], msg_row['provider'],
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
    
    def get_message_history(
        self,
        phone: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
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
        
        if start_date:
            query += " AND completed_at >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND completed_at <= ?"
            params.append(end_date)
        
        query += " ORDER BY completed_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
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
                (phone, message, pdf_url, provider, status, retry_count, 
                 next_retry_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', 0, ?, ?, ?)
                """,
                (
                    row['phone'], row['message'], row['pdf_url'],
                    row['provider'], datetime.now(),
                    row['created_at'], datetime.now()
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
            Dict with 'sent' and 'failed' counts
        """
        query = "SELECT status, COUNT(*) as count FROM message_history WHERE 1=1"
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
        
        query += " GROUP BY status"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            counts = {'sent': 0, 'failed': 0}
            for row in rows:
                if row['status'] in counts:
                    counts[row['status']] = row['count']
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
                "SELECT COUNT(*) FROM message_history WHERE completed_at >= ?",
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


# Global instance
message_db = MessageQueueDB()
