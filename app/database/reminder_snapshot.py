"""
SQLite snapshot store for payment reminder party calculations.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

from app.config import get_local_appdata_path

logger = structlog.get_logger()


def _get_default_snapshot_db_path() -> Path:
    appdata = get_local_appdata_path()
    data_dir = appdata / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "reminder_snapshot.db"


class ReminderSnapshotDB:
    """Stores reminder-party calculation snapshots for fast list queries."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else _get_default_snapshot_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_party_snapshot (
                    party_code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    print_name TEXT,
                    phone TEXT,
                    closing_balance REAL NOT NULL DEFAULT 0,
                    recent_sales_total REAL NOT NULL DEFAULT 0,
                    amount_due REAL NOT NULL DEFAULT 0,
                    sales_credit_days INTEGER NOT NULL DEFAULT 30,
                    credit_days_source TEXT NOT NULL DEFAULT 'config_default',
                    permanent_enabled INTEGER NOT NULL DEFAULT 0,
                    computed_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_snapshot_meta (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_refreshed_at TEXT,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    row_count INTEGER NOT NULL DEFAULT 0,
                    nonzero_count INTEGER NOT NULL DEFAULT 0,
                    error_count INTEGER NOT NULL DEFAULT 0,
                    source_db_path_hash TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO reminder_snapshot_meta (
                    id, last_refreshed_at, duration_ms, row_count, nonzero_count, error_count, source_db_path_hash
                ) VALUES (1, NULL, 0, 0, 0, 0, NULL)
                """
            )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_snapshot_amount_due ON reminder_party_snapshot(amount_due)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_snapshot_name ON reminder_party_snapshot(name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_snapshot_credit_days ON reminder_party_snapshot(sales_credit_days)"
            )
            conn.commit()

            logger.info("reminder_snapshot_db_initialized", db_path=str(self.db_path))

    def replace_snapshot(
        self,
        rows: List[Dict[str, Any]],
        *,
        duration_ms: int,
        row_count: int,
        nonzero_count: int,
        error_count: int,
        source_db_path_hash: str,
    ) -> None:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("BEGIN")
            conn.execute("DELETE FROM reminder_party_snapshot")
            conn.executemany(
                """
                INSERT INTO reminder_party_snapshot (
                    party_code, name, print_name, phone,
                    closing_balance, recent_sales_total, amount_due,
                    sales_credit_days, credit_days_source, permanent_enabled, computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r["party_code"],
                        r["name"],
                        r.get("print_name"),
                        r.get("phone"),
                        float(r.get("closing_balance", 0)),
                        float(r.get("recent_sales_total", 0)),
                        float(r.get("amount_due", 0)),
                        int(r.get("sales_credit_days", 30)),
                        r.get("credit_days_source", "config_default"),
                        int(bool(r.get("permanent_enabled", False))),
                        now,
                    )
                    for r in rows
                ],
            )
            conn.execute(
                """
                UPDATE reminder_snapshot_meta
                SET last_refreshed_at = ?, duration_ms = ?, row_count = ?,
                    nonzero_count = ?, error_count = ?, source_db_path_hash = ?
                WHERE id = 1
                """,
                (now, duration_ms, row_count, nonzero_count, error_count, source_db_path_hash),
            )
            conn.commit()

    def update_party_permanent_enabled(self, party_code: str, enabled: bool) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE reminder_party_snapshot SET permanent_enabled = ? WHERE party_code = ?",
                (1 if enabled else 0, party_code),
            )
            conn.commit()

    def get_status(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT last_refreshed_at, duration_ms, row_count, nonzero_count, error_count, source_db_path_hash
                FROM reminder_snapshot_meta
                WHERE id = 1
                """
            ).fetchone()
            if not row:
                return {
                    "has_snapshot": False,
                    "last_refreshed_at": None,
                    "duration_ms": 0,
                    "row_count": 0,
                    "nonzero_count": 0,
                    "error_count": 0,
                    "source_db_path_hash": None,
                }
            return {
                "has_snapshot": bool(row["last_refreshed_at"]),
                "last_refreshed_at": row["last_refreshed_at"],
                "duration_ms": int(row["duration_ms"] or 0),
                "row_count": int(row["row_count"] or 0),
                "nonzero_count": int(row["nonzero_count"] or 0),
                "error_count": int(row["error_count"] or 0),
                "source_db_path_hash": row["source_db_path_hash"],
            }

    def query_parties(
        self,
        *,
        search: Optional[str],
        filter_by: str,
        min_amount: Optional[float],
        include_zero: bool,
        sort_by: str,
        sort_order: str,
        offset: int,
        limit: int,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        valid_sort_map = {
            "amount_due": "amount_due",
            "name": "name",
            "credit_days": "sales_credit_days",
            "code": "party_code",
        }
        order_col = valid_sort_map.get(sort_by, "amount_due")
        order_dir = "ASC" if str(sort_order).lower() == "asc" else "DESC"

        where_parts = []
        params: List[Any] = []

        if not include_zero:
            where_parts.append("amount_due > 0")
        if min_amount is not None:
            where_parts.append("amount_due >= ?")
            params.append(float(min_amount))
        if search:
            where_parts.append("(LOWER(name) LIKE ? OR party_code LIKE ? OR LOWER(COALESCE(phone, '')) LIKE ?)")
            like = f"%{search.lower()}%"
            params.extend([like, f"%{search}%", like])
        if filter_by == "enabled":
            where_parts.append("permanent_enabled = 1")
        elif filter_by == "disabled":
            where_parts.append("permanent_enabled = 0")

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        with self._get_connection() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS c FROM reminder_party_snapshot {where_clause}",
                params,
            ).fetchone()["c"]

            rows = conn.execute(
                f"""
                SELECT
                    party_code, name, print_name, phone,
                    closing_balance, recent_sales_total, amount_due,
                    sales_credit_days, credit_days_source, permanent_enabled, computed_at
                FROM reminder_party_snapshot
                {where_clause}
                ORDER BY {order_col} {order_dir}, party_code ASC
                LIMIT ? OFFSET ?
                """,
                [*params, int(limit), int(offset)],
            ).fetchall()

            return int(total), [dict(r) for r in rows]


reminder_snapshot_db = ReminderSnapshotDB()

