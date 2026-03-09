"""
Bulk reminder snapshot computation service.
"""

from __future__ import annotations

import hashlib
import time
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

import structlog

from app.database.connection import db
from app.database.reminder_snapshot import reminder_snapshot_db
from app.services.amount_due_calculator import amount_due_calculator
from app.services.ledger_data_service import ledger_data_service
from app.services.reminder_config_service import reminder_config_service

logger = structlog.get_logger()


class ReminderSnapshotService:
    """Computes and persists exact amount-due snapshot for all debtor parties."""

    def __init__(self):
        self.db = db
        self.snapshot_db = reminder_snapshot_db
        self.calculator = amount_due_calculator
        self.config_service = reminder_config_service
        self._chunk_size = 500

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        return Decimal(str(value))

    def _fetch_debtor_roster(self, company_id: str = "default") -> List[Dict[str, Any]]:
        debtor_groups = self.calculator._get_debtor_group_codes(company_id=company_id)  # intentionally shared canonical resolver
        if not debtor_groups:
            return []
        in_clause = ",".join(str(c) for c in debtor_groups)
        query = f"""
            SELECT Code, Name, PrintName, C3 as Phone, I2 as SalesCreditDays
            FROM Master1
            WHERE MasterType = 2
              AND ParentGrp IN ({in_clause})
            ORDER BY Code
        """
        with self.db.get_cursor(company_id=company_id) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        roster: List[Dict[str, Any]] = []
        for r in rows:
            raw_days = r[4]
            has_master_days = raw_days is not None and int(raw_days or 0) > 0
            days = int(raw_days) if has_master_days else int(self.calculator.default_credit_days)
            roster.append(
                {
                    "party_code": str(r[0]),
                    "name": str(r[1] or ""),
                    "print_name": r[2],
                    "phone": r[3],
                    "sales_credit_days": days,
                    "credit_days_source": "master1_i2" if has_master_days else "config_default",
                }
            )
        return roster

    def refresh_snapshot(self, *, as_of_date: Optional[date] = None, company_id: str = "default") -> Dict[str, Any]:
        if as_of_date is None:
            as_of_date = date.today()

        t0 = time.perf_counter()
        roster = self._fetch_debtor_roster(company_id=company_id)
        
        # Determine the current db path for this company to hash
        if company_id in self.db.settings.database.companies:
            current_db_path = self.db.settings.database.companies[company_id].bds_file_path
        elif company_id == "default" and self.db.settings.database.bds_file_path:
            current_db_path = self.db.settings.database.bds_file_path
        else:
            current_db_path = ""
            
        if not roster:
            self.snapshot_db.replace_snapshot(
                [],
                duration_ms=0,
                row_count=0,
                nonzero_count=0,
                error_count=0,
                source_db_path_hash=hashlib.sha256((current_db_path).encode("utf-8")).hexdigest(),
                company_id=company_id,
            )
            return self.snapshot_db.get_status(company_id=company_id)

        config = self.config_service.get_config(scope_key=company_id)
        permanent_map = {int(k): bool(v.enabled) for k, v in config.parties.items() if str(k).isdigit()}

        party_credit_days = {
            int(r["party_code"]): int(r["sales_credit_days"])
            for r in roster
        }
        summary_map = ledger_data_service.compute_party_balances_and_recent_sales(
            party_credit_days=party_credit_days,
            as_of_date=as_of_date,
            company_id=company_id,
        )

        snapshot_rows: List[Dict[str, Any]] = []
        nonzero_count = 0
        for r in roster:
            party_code = r["party_code"]
            summary = summary_map.get(int(party_code), {})
            closing = Decimal(str(summary.get("closing_balance", 0)))
            recent_sales = Decimal(str(summary.get("recent_sales_total", 0)))
            amount_due = Decimal(str(summary.get("amount_due", 0)))
            if amount_due > 0:
                nonzero_count += 1
            snapshot_rows.append(
                {
                    "party_code": party_code,
                    "name": r["name"],
                    "print_name": r.get("print_name"),
                    "phone": r.get("phone"),
                    "closing_balance": closing,
                    "recent_sales_total": recent_sales,
                    "amount_due": amount_due,
                    "sales_credit_days": r["sales_credit_days"],
                    "credit_days_source": r["credit_days_source"],
                    "permanent_enabled": permanent_map.get(int(party_code), False),
                }
            )

        duration_ms = int((time.perf_counter() - t0) * 1000)
        path_hash = hashlib.sha256((current_db_path).encode("utf-8")).hexdigest()
        self.snapshot_db.replace_snapshot(
            snapshot_rows,
            duration_ms=duration_ms,
            row_count=len(snapshot_rows),
            nonzero_count=nonzero_count,
            error_count=0,
            source_db_path_hash=path_hash,
            company_id=company_id,
        )

        status = self.snapshot_db.get_status(company_id=company_id)
        logger.info(
            "reminder_snapshot_refreshed",
            row_count=status["row_count"],
            nonzero_count=status["nonzero_count"],
            duration_ms=status["duration_ms"],
        )

        # Record refresh stats for rolling average progress tracking
        try:
            self.config_service.record_refresh_completed(duration_ms, scope_key=company_id)
        except Exception as e:
            logger.warning("failed_to_record_refresh_stats", error=str(e))

        return status


reminder_snapshot_service = ReminderSnapshotService()
