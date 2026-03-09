"""
Amount Due Calculator Service

Calculates amount due based on:
- Closing balance from ledger
- Recent sales transactions within credit period
- Credit days from Master1.I2 (with fallback to default)
"""
import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

import structlog

from app.constants.reminder_constants import (
    DEFAULT_CREDIT_DAYS,
    MASTER1_SALES_CREDIT_DAYS_COLUMN,
)
from app.database.connection import db
from app.exceptions.ledger_exceptions import NoTransactionsError
from app.models.reminder_schemas import AmountDueCalculation, PartyReminderInfo
from app.services.ledger_data_service import ledger_data_service
from app.services.reminder_config_service import reminder_config_service
from app.utils.number_format import format_indian_currency

logger = structlog.get_logger()


class AmountDueCalculator:
    """Calculate amount due based on credit days and recent sales"""
    
    def __init__(self):
        self.db = db
        self.config_service = reminder_config_service
        self.default_credit_days = DEFAULT_CREDIT_DAYS
        self._debtor_group_codes_cache: Dict[str, List[int]] = {}
    
    def _validate_party_code(self, party_code: str) -> int:
        """Validate and convert party code to integer"""
        try:
            code_int = int(party_code.strip())
            if code_int <= 0:
                raise ValueError("Party code must be positive")
            return code_int
        except (ValueError, AttributeError) as e:
            logger.error("invalid_party_code", party_code=party_code, error=str(e))
            raise ValueError(f"Invalid party code: {party_code}") from e
    
    def get_credit_days(self, party_code: str, override: Optional[int] = None, company_id: str = "default") -> Tuple[int, str]:
        """
        Get credit days for a party from Master1.I2
        
        Returns:
            Tuple of (credit_days, source)
            Source can be: "override", "master1_i2", or "config_default"
        """
        # Check override first
        if override is not None and 1 <= override <= 365:
            logger.debug("using_credit_days_override", party_code=party_code, days=override)
            return override, "override"
        
        party_code_int = self._validate_party_code(party_code)
        
        try:
            query = """
                SELECT I2
                FROM Master1
                WHERE Code = ? AND MasterType = 2
            """
            
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute(query, (party_code_int,))
                row = cursor.fetchone()
                
                if row and row[0] and row[0] > 0:
                    credit_days = int(row[0])
                    logger.debug(
                        "credit_days_from_master1",
                        party_code=party_code,
                        days=credit_days,
                        column=MASTER1_SALES_CREDIT_DAYS_COLUMN
                    )
                    return credit_days, "master1_i2"
                else:
                    logger.debug(
                        "credit_days_not_set_in_master1",
                        party_code=party_code,
                        using_default=self.default_credit_days
                    )
                    return self.default_credit_days, "config_default"
                    
        except Exception as e:
            logger.error(
                "error_fetching_credit_days",
                company_id=company_id,
                party_code=party_code,
                error=str(e)
            )
            return self.default_credit_days, "config_default"
    
    def get_recent_sales(
        self,
        party_code: str,
        days: int,
        as_of_date: Optional[date] = None,
        company_id: str = "default"
    ) -> Tuple[Decimal, int, date, date]:
        """
        Get total sales amount within the last N days
        
        Args:
            party_code: Party code
            days: Number of days to look back
            as_of_date: Calculate as of this date (default: today)
            
        Returns:
            Tuple of (total_sales, transaction_count, start_date, end_date)
        """
        party_code_int = self._validate_party_code(party_code)
        
        if as_of_date is None:
            as_of_date = date.today()
        
        start_date = as_of_date - timedelta(days=days)
        
        try:
            # Query Tran1 for sales transactions (VchType = 9)
            # Note: Sales increase Dr balance (customer owes more)
            query = """
                SELECT SUM(IIF(ISNULL(t1.VchAmtBaseCur), 0, t1.VchAmtBaseCur)), COUNT(*)
                FROM Tran1 t1
                INNER JOIN Tran2 t2 ON t1.VchCode = t2.VchCode
                WHERE t2.MasterCode1 = ?
                AND t1.VchType = 9
                AND t1.Date >= ?
                AND t1.Date <= ?
                AND (t1.Cancelled = 0 OR t1.Cancelled IS NULL)
            """
            
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute(query, (party_code_int, start_date, as_of_date))
                row = cursor.fetchone()
                
                if row and row[0]:
                    total_sales = Decimal(str(row[0]))
                    count = int(row[1])
                else:
                    total_sales = Decimal("0")
                    count = 0
                
                logger.debug(
                    "recent_sales_calculated",
                    party_code=party_code,
                    days=days,
                    start_date=start_date,
                    end_date=as_of_date,
                    total_sales=total_sales,
                    count=count
                )
                
                return total_sales, count, start_date, as_of_date
                
        except Exception as e:
            logger.error(
                "error_calculating_recent_sales",
                party_code=party_code,
                days=days,
                error=str(e)
            )
            return Decimal("0"), 0, start_date, as_of_date

    def _get_debtor_group_codes(self, force_refresh: bool = False, company_id: str = "default") -> List[int]:
        """
        Resolve debtor account-group codes from Master1 hierarchy.

        Busy stores account groups in Master1 with MasterType = 1 and ledgers
        with MasterType = 2. Debtor ledgers are expected under "Sundry Debtors"
        (or debtor-like group names), including all descendant groups.
        """
        if company_id in self._debtor_group_codes_cache and not force_refresh:
            return self._debtor_group_codes_cache[company_id]

        groups: List[Tuple[int, str, int]] = []
        with self.db.get_cursor(company_id=company_id) as cursor:
            cursor.execute(
                """
                SELECT Code, Name, ParentGrp
                FROM Master1
                WHERE MasterType = 1
                """
            )
            groups = [(int(r[0]), str(r[1] or ""), int(r[2] or 0)) for r in cursor.fetchall()]

        by_parent: Dict[int, List[int]] = {}
        for code, _name, parent in groups:
            by_parent.setdefault(parent, []).append(code)

        seeds: Set[int] = set()
        for code, name, _parent in groups:
            lname = name.lower().strip()
            if "sundry debtors" in lname or "debtor" in lname:
                seeds.add(code)

        # Conservative fallback for common Busy setups.
        if not seeds:
            for code, _name, _parent in groups:
                if code == 116:
                    seeds.add(code)
                    break

        all_group_codes: Set[int] = set()
        stack = list(seeds)
        while stack:
            cur = stack.pop()
            all_group_codes.add(cur)
            stack.extend(by_parent.get(cur, []))

        resolved = sorted(all_group_codes)
        self._debtor_group_codes_cache[company_id] = resolved
        logger.info(
            "debtor_groups_resolved",
            seed_count=len(seeds),
            group_count=len(resolved),
            groups=resolved[:20],
        )
        return resolved

    def get_debtor_party_count(self, company_id: str = "default") -> int:
        """Count ledger masters that fall under debtor group hierarchy."""
        debtor_groups = self._get_debtor_group_codes(company_id=company_id)
        if not debtor_groups:
            return 0
        in_clause = ",".join(str(c) for c in debtor_groups)
        with self.db.get_cursor(company_id=company_id) as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM Master1
                WHERE MasterType = 2
                  AND ParentGrp IN ({in_clause})
                """
            )
            return int((cursor.fetchone() or [0])[0] or 0)
    
    async def calculate_for_party(
        self,
        party_code: str,
        credit_days: Optional[int] = None,
        as_of_date: Optional[date] = None,
        company_id: str = "default"
    ) -> AmountDueCalculation:
        """Async wrapper to keep blocking ODBC reads off the event loop."""
        return await asyncio.to_thread(
            self._calculate_for_party_sync,
            party_code,
            credit_days,
            as_of_date,
            company_id,
        )

    def _calculate_for_party_sync(
        self,
        party_code: str,
        credit_days: Optional[int] = None,
        as_of_date: Optional[date] = None,
        company_id: str = "default"
    ) -> AmountDueCalculation:
        """
        Calculate amount due for a single party
        
        Formula: Amount Due = Closing Balance - Recent Sales
        
        Args:
            party_code: Party code
            credit_days: Override credit days (optional)
            as_of_date: Calculate as of this date (default: today)
            
        Returns:
            AmountDueCalculation with full details
        """
        logger.info("calculating_amount_due", company_id=company_id, party_code=party_code)
        
        try:
            # Get party info
            customer_info = ledger_data_service.get_customer_info(party_code, company_id=company_id)
            
            # Get credit days
            credit_days_used, credit_days_source = self.get_credit_days(party_code, credit_days, company_id=company_id)
            
            # Get ledger for closing balance
            ledger = ledger_data_service.generate_ledger_report(party_code, company_id=company_id)
            closing_balance = ledger.closing_balance
            
            # Get recent sales
            recent_sales, sales_count, start_date, end_date = self.get_recent_sales(
                party_code, credit_days_used, as_of_date, company_id=company_id
            )
            
            # Calculate amount due
            amount_due = closing_balance - recent_sales
            
            logger.info(
                "amount_due_calculated",
                company_id=company_id,
                party_code=party_code,
                closing_balance=closing_balance,
                credit_days=credit_days_used,
                recent_sales=recent_sales,
                amount_due=amount_due
            )
            
            return AmountDueCalculation(
                party_code=party_code,
                party_name=customer_info.name,
                closing_balance=closing_balance,
                credit_days_used=credit_days_used,
                credit_days_source=credit_days_source,
                recent_sales_total=recent_sales,
                recent_sales_count=sales_count,
                recent_sales_date_range=(start_date, end_date),
                amount_due=amount_due,
                calculation_timestamp=datetime.now()
            )
            
        except NoTransactionsError as e:
            logger.debug(
                "party_has_no_transactions",
                party_code=party_code,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "error_calculating_amount_due",
                party_code=party_code,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def calculate_for_all_parties(
        self,
        min_amount_due: Decimal = Decimal("0.01"),
        as_of_date: Optional[date] = None,
        max_parties: Optional[int] = None,
        company_id: str = "default"
    ) -> List[PartyReminderInfo]:
        """
        Calculate amount due for all parties with positive balance
        
        Args:
            min_amount_due: Minimum amount due to include (default: 0.01)
            as_of_date: Calculate as of this date
            
        Returns:
            List of PartyReminderInfo sorted by amount due (descending)
        """
        logger.info("calculating_amount_due_for_all_parties", min_amount_due=min_amount_due)
        
        eligible_parties: List[PartyReminderInfo] = []

        try:
            from app.services.reminder_snapshot_service import reminder_snapshot_service

            snapshot_status = await asyncio.to_thread(
                reminder_snapshot_service.refresh_snapshot,
                as_of_date=as_of_date,
                company_id=company_id,
            )
            logger.info(
                "eligible_parties_calculated",
                eligible_count=int(snapshot_status.get("nonzero_count") or 0),
                mode="snapshot",
            )

            config = self.config_service.get_config(scope_key=company_id)
            currency = config.currency_symbol
            total, rows = reminder_snapshot_service.snapshot_db.query_parties(
                search=None,
                filter_by="all",
                min_amount=float(min_amount_due),
                include_zero=False,
                sort_by="amount_due",
                sort_order="desc",
                offset=0,
                limit=int(max_parties) if max_parties else 100000,
                company_id=company_id,
            )

            for row in rows:
                eligible_parties.append(
                    PartyReminderInfo(
                        code=str(row["party_code"]),
                        name=row["name"],
                        print_name=row.get("print_name"),
                        phone=row.get("phone"),
                        closing_balance=Decimal(str(row.get("closing_balance") or 0)),
                        closing_balance_formatted=format_indian_currency(
                            Decimal(str(row.get("closing_balance") or 0)), symbol=currency
                        ),
                        amount_due=Decimal(str(row.get("amount_due") or 0)),
                        amount_due_formatted=format_indian_currency(
                            Decimal(str(row.get("amount_due") or 0)), symbol=currency
                        ),
                        sales_credit_days=int(row.get("sales_credit_days") or self.default_credit_days),
                        credit_days_source=str(row.get("credit_days_source") or "config_default"),
                        permanent_enabled=bool(row.get("permanent_enabled")),
                        temp_enabled=False,
                    )
                )

            logger.info(
                "eligible_parties_loaded_from_snapshot",
                total=total,
                returned=len(eligible_parties),
            )
            return eligible_parties

        except Exception as e:
            logger.error(
                "error_calculating_all_parties",
                error=str(e),
                exc_info=True,
            )
            raise
    
    def format_amount(self, amount: Decimal, company_id: str = "default") -> str:
        """Format amount with currency symbol"""
        config = self.config_service.get_config(scope_key=company_id)
        return format_indian_currency(amount, symbol=config.currency_symbol)


# Global instance
amount_due_calculator = AmountDueCalculator()
