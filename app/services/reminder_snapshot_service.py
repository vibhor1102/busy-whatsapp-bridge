"""
Bulk reminder snapshot computation service.
"""

from __future__ import annotations

import hashlib
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import structlog

from app.constants.ledger_constants import VoucherType
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

    @staticmethod
    def _fmt_access_date(dt: date) -> str:
        return dt.strftime("%m/%d/%Y")

    @staticmethod
    def _signed_contribution(vch_type: int, value1: Decimal) -> Decimal:
        """
        Mirror ledger_data_service debit/credit effect as signed contribution.
        Positive contribution increases closing balance, negative decreases.
        """
        if vch_type in (VoucherType.CONTRA, VoucherType.JOURNAL):
            return -value1
        if vch_type in (VoucherType.SALES, VoucherType.PAYMENT_CASH, VoucherType.PAYMENT_BANK, VoucherType.CREDIT_NOTE):
            return abs(value1)
        if vch_type in (VoucherType.PURCHASE, VoucherType.RECEIPT, VoucherType.RECEIPT_ALT, VoucherType.DEBIT_NOTE):
            return -abs(value1)
        return -value1

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

        party_codes_int = [int(r["party_code"]) for r in roster]
        party_code_set = set(party_codes_int)

        # seed closing balances with opening balance from Folio1
        closing_map: Dict[int, Decimal] = {c: Decimal("0") for c in party_codes_int}
        recent_sales_map: Dict[int, Decimal] = {c: Decimal("0") for c in party_codes_int}
        recent_sales_count: Dict[int, int] = {c: 0 for c in party_codes_int}

        # per-party sales cutoff based on credit days
        cutoff_map: Dict[int, date] = {}
        for r in roster:
            pcode = int(r["party_code"])
            cutoff_map[pcode] = as_of_date - timedelta(days=int(r["sales_credit_days"]))

        # Opening balances (Folio1)
        for i in range(0, len(party_codes_int), self._chunk_size):
            chunk = party_codes_int[i : i + self._chunk_size]
            in_clause = ",".join(str(c) for c in chunk)
            query = f"""
                SELECT MasterCode, D1
                FROM Folio1
                WHERE MasterType = 2
                  AND MasterCode IN ({in_clause})
            """
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute(query)
                for row in cursor.fetchall():
                    closing_map[int(row[0])] = self._to_decimal(row[1])

        fy = ledger_data_service.get_financial_year(company_id=company_id)
        start_s = self._fmt_access_date(fy.start_date)
        end_s = self._fmt_access_date(fy.end_date)

        # Voucher effects + recent sales in one scan per chunk
        for i in range(0, len(party_codes_int), self._chunk_size):
            chunk = party_codes_int[i : i + self._chunk_size]
            chunk_set = set(chunk)
            in_clause = ",".join(str(c) for c in chunk)
            query = f"""
                SELECT
                    t2.MasterCode1,
                    t2.MasterCode2,
                    t2.Value1,
                    t1.VchType,
                    t1.Date,
                    t1.VchAmtBaseCur
                FROM Tran2 t2
                INNER JOIN Tran1 t1 ON t1.VchCode = t2.VchCode
                WHERE t2.RecType = 1
                  AND t1.Date >= #{start_s}#
                  AND t1.Date <= #{end_s}#
                  AND (t2.MasterCode1 IN ({in_clause}) OR t2.MasterCode2 IN ({in_clause}))
            """
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute(query)
                for row in cursor.fetchall():
                    mc1 = int(row[0] or 0)
                    mc2 = int(row[1] or 0)
                    v1 = self._to_decimal(row[2])
                    vtype = int(row[3] or 0)
                    vdate = row[4]
                    vamt = self._to_decimal(row[5])

                    party_code = mc1 if mc1 in chunk_set else (mc2 if mc2 in chunk_set else 0)
                    if party_code and party_code in party_code_set:
                        closing_map[party_code] += self._signed_contribution(vtype, v1)

                    # recent sales: only when debtor is MasterCode1 (same as existing logic)
                    if vtype == VoucherType.SALES and mc1 in chunk_set and mc1 in party_code_set:
                        if isinstance(vdate, datetime):
                            txn_date = vdate.date()
                        elif isinstance(vdate, date):
                            txn_date = vdate
                        else:
                            txn_date = as_of_date
                        if cutoff_map[mc1] <= txn_date <= as_of_date:
                            recent_sales_map[mc1] += vamt
                            recent_sales_count[mc1] += 1

        config = self.config_service.get_config(scope_key=company_id)
        permanent_map = {int(k): bool(v.enabled) for k, v in config.parties.items() if str(k).isdigit()}

        snapshot_rows: List[Dict[str, Any]] = []
        nonzero_count = 0
        for r in roster:
            pcode = int(r["party_code"])
            closing = closing_map.get(pcode, Decimal("0"))
            recent_sales = recent_sales_map.get(pcode, Decimal("0"))
            amount_due = closing - recent_sales
            if amount_due > 0:
                nonzero_count += 1
            snapshot_rows.append(
                {
                    "party_code": r["party_code"],
                    "name": r["name"],
                    "print_name": r.get("print_name"),
                    "phone": r.get("phone"),
                    "closing_balance": closing,
                    "recent_sales_total": recent_sales,
                    "amount_due": amount_due,
                    "sales_credit_days": r["sales_credit_days"],
                    "credit_days_source": r["credit_days_source"],
                    "permanent_enabled": permanent_map.get(pcode, False),
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
