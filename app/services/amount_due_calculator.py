"""
Amount Due Calculator Service

Calculates amount due based on:
- Closing balance from ledger
- Recent sales transactions within credit period
- Credit days from Master1.I2 (with fallback to default)
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

import structlog

from app.constants.reminder_constants import (
    DEFAULT_CREDIT_DAYS,
    MASTER1_SALES_CREDIT_DAYS_COLUMN,
    CURRENCY_SYMBOL,
)
from app.database.connection import db
from app.models.reminder_schemas import AmountDueCalculation, PartyReminderInfo
from app.services.ledger_data_service import ledger_data_service

logger = structlog.get_logger()


class AmountDueCalculator:
    """Calculate amount due based on credit days and recent sales"""
    
    def __init__(self):
        self.db = db
        self.default_credit_days = DEFAULT_CREDIT_DAYS
    
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
    
    def get_credit_days(self, party_code: str, override: Optional[int] = None) -> Tuple[int, str]:
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
            query = f"""
                SELECT {MASTER1_SALES_CREDIT_DAYS_COLUMN}
                FROM Master1
                WHERE Code = {party_code_int} AND MasterType = 2
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(query)
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
                party_code=party_code,
                error=str(e)
            )
            return self.default_credit_days, "config_default"
    
    def get_recent_sales(
        self,
        party_code: str,
        days: int,
        as_of_date: Optional[date] = None
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
            query = f"""
                SELECT SUM(t1.VchAmtBaseCur), COUNT(*)
                FROM Tran1 t1
                INNER JOIN Tran2 t2 ON t1.VchCode = t2.VchCode
                WHERE t2.MasterCode1 = {party_code_int}
                AND t1.VchType = 9
                AND t1.Date >= #{start_date.strftime('%m/%d/%Y')}#
                AND t1.Date <= #{as_of_date.strftime('%m/%d/%Y')}#
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(query)
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
    
    async def calculate_for_party(
        self,
        party_code: str,
        credit_days: Optional[int] = None,
        as_of_date: Optional[date] = None
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
        logger.info("calculating_amount_due", party_code=party_code)
        
        try:
            # Get party info
            customer_info = ledger_data_service.get_customer_info(party_code)
            
            # Get credit days
            credit_days_used, credit_days_source = self.get_credit_days(party_code, credit_days)
            
            # Get ledger for closing balance
            ledger = ledger_data_service.generate_ledger_report(party_code)
            closing_balance = ledger.closing_balance
            
            # Get recent sales
            recent_sales, sales_count, start_date, end_date = self.get_recent_sales(
                party_code, credit_days_used, as_of_date
            )
            
            # Calculate amount due
            amount_due = closing_balance - recent_sales
            
            logger.info(
                "amount_due_calculated",
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
        as_of_date: Optional[date] = None
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
            # Get all parties from Master1
            query = """
                SELECT Code, Name, PrintName, C3 as Phone
                FROM Master1
                WHERE MasterType = 2
                ORDER BY Code
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(query)
                parties = cursor.fetchall()
            
            logger.info("total_parties_found", count=len(parties))
            
            for party_row in parties:
                try:
                    party_code = str(party_row[0])
                    party_name = party_row[1]
                    print_name = party_row[2]
                    phone = party_row[3]
                    
                    # Calculate amount due
                    calculation = await self.calculate_for_party(party_code, as_of_date=as_of_date)
                    
                    # Check if meets minimum threshold
                    if calculation.amount_due >= min_amount_due:
                        # Format amounts
                        closing_formatted = f"{CURRENCY_SYMBOL}{calculation.closing_balance:,.2f}"
                        amount_due_formatted = f"{CURRENCY_SYMBOL}{calculation.amount_due:,.2f}"
                        
                        party_info = PartyReminderInfo(
                            code=party_code,
                            name=party_name,
                            print_name=print_name,
                            phone=phone,
                            closing_balance=calculation.closing_balance,
                            closing_balance_formatted=closing_formatted,
                            amount_due=calculation.amount_due,
                            amount_due_formatted=amount_due_formatted,
                            sales_credit_days=calculation.credit_days_used,
                            credit_days_source=calculation.credit_days_source,
                            permanent_enabled=False,  # Will be populated from config
                            temp_enabled=False
                        )
                        
                        eligible_parties.append(party_info)
                        
                except Exception as e:
                    logger.warning(
                        "error_processing_party",
                        party_code=party_code,
                        error=str(e)
                    )
                    continue
            
            # Sort by amount due descending
            eligible_parties.sort(key=lambda x: x.amount_due, reverse=True)
            
            logger.info(
                "eligible_parties_calculated",
                total_parties=len(parties),
                eligible_count=len(eligible_parties)
            )
            
            return eligible_parties
            
        except Exception as e:
            logger.error(
                "error_calculating_all_parties",
                error=str(e),
                exc_info=True
            )
            raise
    
    def format_amount(self, amount: Decimal) -> str:
        """Format amount with currency symbol"""
        return f"{CURRENCY_SYMBOL}{amount:,.2f}"


# Global instance
amount_due_calculator = AmountDueCalculator()
