"""
Service to fetch ledger data from Busy Accounting database.
Refactored for universality - works with any Busy database configuration.
"""
import structlog
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional, Dict, Set, Tuple

from app.database.connection import db
from app.models.ledger_schemas import (
    LedgerEntry,
    CustomerInfo,
    CompanyInfo,
    FinancialYearInfo,
    LedgerReport
)
from app.exceptions.ledger_exceptions import (
    PartyNotFoundError,
    NoTransactionsError,
)
from app.constants.ledger_constants import (
    RecType,
    MasterType,
    VoucherType,
    ConfigRecType,
    VOUCHER_TYPE_NAMES,
    BANK_KEYWORDS,
    SALES_KEYWORDS,
    PURCHASE_KEYWORDS,
    ROUNDING_KEYWORDS,
    DEFAULT_COUNTER_ACCOUNT,
    DATE_FORMATS,
)

logger = structlog.get_logger()


class LedgerDataService:
    """
    Fetch and format ledger data from Busy Accounting database.
    
    This service is designed to work with any Busy database configuration
    and extracts all configuration dynamically from the database.
    """
    
    def __init__(self):
        self.db = db
        self._financial_year_cache: Dict[str, FinancialYearInfo] = {}
        self._company_info_cache: Dict[str, CompanyInfo] = {}
    
    def _validate_party_code(self, party_code: str) -> int:
        """
        Validate and convert party code to integer.
        
        Args:
            party_code: String party code from user input
            
        Returns:
            Integer party code
            
        Raises:
            PartyNotFoundError: If party code is invalid
        """
        if not party_code or not party_code.strip():
            raise PartyNotFoundError(party_code, "Party code cannot be empty")
        
        try:
            code_int = int(party_code.strip())
            if code_int <= 0:
                raise ValueError("Party code must be positive")
            return code_int
        except ValueError as e:
            raise PartyNotFoundError(
                party_code, 
                f"Invalid party code format: {str(e)}"
            ) from e
    
    def _parse_date(self, date_value) -> date:
        """
        Parse date from various formats.
        
        Handles datetime objects, date objects, and string formats.
        Returns today's date only as a last resort fallback.
        """
        if isinstance(date_value, datetime):
            return date_value.date()
        if isinstance(date_value, date):
            return date_value
        
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(str(date_value), fmt).date()
            except ValueError:
                continue
        
        logger.warning(
            "date_parse_failed", 
            date_value=date_value,
            attempted_formats=DATE_FORMATS
        )
        return date.today()

    def _try_parse_date_strict(self, date_value) -> Optional[date]:
        """
        Strict date parsing: returns None if value is not a valid date.
        Does not log warnings for non-date config noise.
        """
        if isinstance(date_value, datetime):
            return date_value.date()
        if isinstance(date_value, date):
            return date_value
        if date_value is None:
            return None

        raw = str(date_value).strip()
        if not raw:
            return None

        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None
    
    def _calculate_year_name(self, start_date: date, end_date: date) -> str:
        """Calculate financial year name (e.g., '2024-25')."""
        if start_date.year == end_date.year:
            return str(start_date.year)
        return f"{start_date.year}-{str(end_date.year)[-2:]}"
    
    def get_financial_year(self, force_refresh: bool = False, company_id: str = "default") -> FinancialYearInfo:
        """
        Calculates financial year based directly on the current date.
        Financial years strictly run April 1st to March 31st.
        """
        if company_id in self._financial_year_cache and not force_refresh:
            return self._financial_year_cache[company_id]
        
        today = date.today()
        
        if today.month >= 4:
            fy_start = date(today.year, 4, 1)
            fy_end = date(today.year + 1, 3, 31)
        else:
            fy_start = date(today.year - 1, 4, 1)
            fy_end = date(today.year, 3, 31)
        
        year_name = self._calculate_year_name(fy_start, fy_end)
        
        logger.info(
            "financial_year_calculated",
            start_date=fy_start,
            end_date=fy_end,
            year_name=year_name
        )
        
        info = FinancialYearInfo(
            start_date=fy_start,
            end_date=fy_end,
            year_name=year_name
        )
        self._financial_year_cache[company_id] = info
        return info
    
    def get_company_info(self, force_refresh: bool = False, company_id: str = "default") -> CompanyInfo:
        """
        Fetch company info.
        
        Priority:
        1) Reminder config company.name (user-configured, most reliable)
        2) Locks.CompanyName from database
        3) Config table with COMPANY_INFO RecType
        4) DB filename as fallback
        
        Returns minimal info if all sources are empty.
        """
        if company_id in self._company_info_cache and not force_refresh:
            return self._company_info_cache[company_id]
        
        # First try: Database specific config directly from memory
        try:
            if company_id in self.db.settings.database.companies:
                company = self.db.settings.database.companies[company_id]
                if company.company_name or company.contact_phone or company.company_address:
                    logger.debug("company_name_from_db_config", company_name=company.company_name)
                    info = CompanyInfo(
                        name=company.company_name,
                        address_line1=company.company_address,
                        phone=company.contact_phone
                    )
                    self._company_info_cache[company_id] = info
                    return info
            # Backwards compatibility check
            elif company_id == 'default':
                company_name = self.db.settings.database.companies.get("default", type("obj", (object,), {"company_name": None})).company_name
                # Fallback to the generic database level configs
                if getattr(self.db.settings.database, 'company_name', None) or getattr(self.db.settings.database, 'contact_phone', None):
                     logger.debug("company_name_from_root_config")
                     info = CompanyInfo(
                        name=getattr(self.db.settings.database, 'company_name', None),
                        address_line1=getattr(self.db.settings.database, 'company_address', None),
                        phone=getattr(self.db.settings.database, 'contact_phone', None)
                     )
                     self._company_info_cache[company_id] = info
                     return info
            
        except Exception as e:
            logger.debug("db_config_company_info_failed", company_id=company_id, error=str(e))
        
        # Second try: Reminder config (user-configured company name fallback)
        try:
            from app.services.reminder_config_service import reminder_config_service
            config = reminder_config_service.get_config(scope_key=company_id)
            if config and config.company and config.company.name:
                company_name = config.company.name.strip()
                if company_name:
                    logger.debug("company_name_from_reminder_config_fallback", company_name=company_name)
                    info = CompanyInfo(
                        name=company_name,
                        address_line1=config.company.address,
                        phone=config.company.contact_phone
                    )
                    self._company_info_cache[company_id] = info
                    return info
        except Exception as e:
            logger.debug("reminder_config_company_name_failed", company_id=company_id, error=str(e))
        
        # Second try: Locks.CompanyName from database
        try:
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute("SELECT TOP 1 CompanyName FROM Locks")
                row = cursor.fetchone()
                if row and row[0] and str(row[0]).strip():
                    company_name = str(row[0]).strip()
                    logger.debug("company_name_from_locks", company_name=company_name)
                    info = CompanyInfo(name=company_name)
                    self._company_info_cache[company_id] = info
                    return info
        except Exception as e:
            logger.debug("locks_company_name_failed", company_id=company_id, error=str(e))
        
        # Third try: Config table
        try:
            query = f"""
                SELECT C1, C2, C3, C4, C5, C6 
                FROM Config 
                WHERE RecType = {ConfigRecType.COMPANY_INFO}
            """
            
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                
                if row and row[0]:
                    info = CompanyInfo(
                        name=row[0],
                        address_line1=row[1],
                        address_line2=row[2],
                        address_line3=row[3],
                        address_line4=row[4],
                        gst_no=row[5]
                    )
                    self._company_info_cache[company_id] = info
                    return info
                    
        except Exception as e:
            logger.debug("config_company_info_failed", company_id=company_id, error=str(e))
        
        # Fallback: Use database filename or generic name
        fallback_name = self._detect_company_name_fallback(company_id=company_id)
        logger.info("company_info_using_fallback", fallback_name=fallback_name)
        info = CompanyInfo(name=fallback_name)
        self._company_info_cache[company_id] = info
        return info

    def _detect_company_name_fallback(self, company_id: str = "default") -> str:
        """
        Best-effort company name when Config rec-type mapping is unavailable.
        Priority:
        1) Locks.CompanyName (if populated)
        2) DB filename stem
        3) Generic fallback
        """
        try:
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute("SELECT TOP 1 CompanyName FROM Locks")
                row = cursor.fetchone()
                if row and row[0] and str(row[0]).strip():
                    return str(row[0]).strip()
        except Exception:
            pass

        # Use DatabaseSettings properties
        if company_id in self.db.settings.database.companies:
            db_path = self.db.settings.database.companies[company_id].bds_file_path
        elif company_id == "default" and self.db.settings.database.bds_file_path:
            db_path = self.db.settings.database.bds_file_path
        else:
            db_path = ""
            
        if db_path:
            stem = Path(db_path).stem.strip()
            if stem:
                return stem
        return "Company"
    
    def get_customer_info(self, party_code: str, company_id: str = "default") -> CustomerInfo:
        """
        Fetch customer details from Master1.
        
        Args:
            party_code: Validated party code
            
        Returns:
            CustomerInfo object with all customer details
            
        Raises:
            PartyNotFoundError: If party not found in database
        """
        party_code_int = self._validate_party_code(party_code)
        
        try:
            master_query = f"""
                SELECT 
                    Code, Name, PrintName, C2 as GSTNo, C1 as Address1, C3 as Phone
                FROM Master1
                WHERE Code = {party_code_int} AND MasterType = {MasterType.PARTY}
            """
            
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute(master_query)
                row = cursor.fetchone()
                
                if not row:
                    logger.error("party_not_found", party_code=party_code)
                    raise PartyNotFoundError(party_code)
                
                code, name, print_name, gst_no, address1, phone = row
                
                # Get additional address info
                address2 = address3 = address4 = None
                try:
                    addr_query = f"""
                        SELECT Address1, Address2, Address3, Address4, Mobile
                        FROM MasterAddressInfo
                        WHERE MasterCode = {party_code_int}
                    """
                    cursor.execute(addr_query)
                    addr_row = cursor.fetchone()
                    if addr_row:
                        if addr_row[0]:
                            address1 = addr_row[0]
                        address2 = addr_row[1]
                        address3 = addr_row[2]
                        address4 = addr_row[3]
                        if addr_row[4]:
                            phone = addr_row[4]
                except Exception as e:
                    logger.debug("master_address_info_query_failed", error=str(e))
                
                return CustomerInfo(
                    code=str(code),
                    name=name,
                    print_name=print_name,
                    gst_no=gst_no,
                    address_line1=address1,
                    address_line2=address2,
                    address_line3=address3,
                    address_line4=address4,
                    phone=phone
                )
                
        except PartyNotFoundError:
            raise
        except Exception as e:
            logger.error("get_customer_info_error", company_id=company_id, party_code=party_code, error=str(e))
            raise PartyNotFoundError(party_code, f"Database error: {str(e)}") from e

    def _get_party_parent_group(self, party_code_int: int, company_id: str = "default") -> Optional[int]:
        """Return parent group code for a party master."""
        try:
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute(
                    f"""
                    SELECT ParentGrp
                    FROM Master1
                    WHERE Code = {party_code_int} AND MasterType = {MasterType.PARTY}
                    """
                )
                row = cursor.fetchone()
                return int(row[0]) if row and row[0] is not None else None
        except Exception as e:
            logger.debug("get_party_parent_group_failed", party_code=party_code_int, error=str(e))
            return None

    def _normalize_opening_balance(
        self,
        raw_balance: Decimal,
        party_code_int: int,
        company_id: str = "default",
    ) -> Decimal:
        """
        Normalize Folio1 opening balance to ledger sign convention.

        Busy opening-balance sign is not reliable across party groups in this
        database. Debtors should open on the Dr side and creditors on the Cr
        side regardless of the raw Folio1 sign.
        """
        parent_group = self._get_party_parent_group(party_code_int, company_id=company_id)
        return self._normalize_opening_balance_for_parent_group(raw_balance, parent_group)

    def _normalize_opening_balance_for_parent_group(
        self,
        raw_balance: Decimal,
        parent_group: Optional[int],
    ) -> Decimal:
        """Normalize Folio1 opening balance when parent group is already known."""
        if parent_group == 116:
            return abs(raw_balance)
        if parent_group == 117:
            return -abs(raw_balance)
        return raw_balance
    
    def get_opening_balance(self, party_code: str, as_of_date: date, company_id: str = "default") -> Decimal:
        """
        Get opening balance for party as of specific date.
        
        Returns 0 if no opening balance found.
        """
        party_code_int = self._validate_party_code(party_code)
        
        try:
            query = f"""
                SELECT D1, D4
                FROM Folio1 
                WHERE MasterCode = {party_code_int} AND MasterType = {MasterType.PARTY}
            """
            
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                
                if row and row[0] is not None:
                    balance = self._normalize_opening_balance(
                        Decimal(str(row[0] or 0)),
                        party_code_int,
                        company_id=company_id,
                    )
                    logger.info(
                        "opening_balance_fetched", 
                        party_code=party_code, 
                        balance=balance
                    )
                    return balance
                else:
                    logger.debug("no_folio_record", party_code=party_code)
                    return Decimal('0')
                    
        except Exception as e:
            logger.warning("get_opening_balance_failed", company_id=company_id, party_code=party_code, error=str(e))
            return Decimal('0')
    
    def get_credit_days(self, party_code: str, company_id: str = "default") -> Tuple[int, str]:
        """
        Get credit days for a party from Master1 table.
        
        Checks Master1.I2 (Sales Credit Days) for the party.
        Returns default if not set or party not found.
        
        Args:
            party_code: Party code
            
        Returns:
            Tuple of (credit_days, source)
            Source indicates where the value came from:
            - "master1_i2": From Master1.I2 column
            - "default": Using default value (30 days)
        """
        from app.constants.reminder_constants import DEFAULT_CREDIT_DAYS
        
        party_code_int = self._validate_party_code(party_code)
        
        try:
            query = f"""
                SELECT I2
                FROM Master1
                WHERE Code = {party_code_int} AND MasterType = {MasterType.PARTY}
            """
            
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                
                if row and row[0] is not None and row[0] > 0:
                    credit_days = int(row[0])
                    logger.debug(
                        "credit_days_fetched_from_master1",
                        party_code=party_code,
                        credit_days=credit_days
                    )
                    return credit_days, "master1_i2"
                else:
                    logger.debug(
                        "credit_days_not_set_using_default",
                        party_code=party_code,
                        default_credit_days=DEFAULT_CREDIT_DAYS
                    )
                    return DEFAULT_CREDIT_DAYS, "default"
                    
        except Exception as e:
            logger.warning(
                "get_credit_days_error",
                company_id=company_id,
                party_code=party_code,
                error=str(e)
            )
            return DEFAULT_CREDIT_DAYS, "default"
    
    def _get_voucher_type_name(self, vch_type: int, vch_no: Optional[str] = None) -> str:
        """Get human-readable voucher type abbreviation."""
        if self._is_credit_note_series(vch_type, vch_no):
            return VOUCHER_TYPE_NAMES[VoucherType.CREDIT_NOTE]
        return VOUCHER_TYPE_NAMES.get(vch_type, "Jrnl")
    
    def _normalize_vch_no(self, vch_no: Optional[str]) -> str:
        """Normalize voucher number for subtype checks."""
        return (vch_no or "").strip().upper()

    def _is_credit_note_series(self, vch_type: int, vch_no: Optional[str]) -> bool:
        """
        Busy stores this credit-note series under type 3 in some datasets.

        Restrict the override to the document-number family so real payments
        of the same numeric type are not flipped accidentally.
        """
        return vch_type == VoucherType.PAYMENT_CASH and self._normalize_vch_no(vch_no).startswith("CN-")

    def _determine_dr_cr(self, vch_type: int, value1: Optional[float], vch_no: Optional[str] = None) -> bool:
        """
        Determine if entry is Dr or Cr based on voucher type and Value1 sign.
        
        Business Logic (from Business POV):
        - Sales (Type 9): Dr (customer owes us more)
        - Purchase (Type 2): Cr (purchase return / liability reduction)
        - Receipt (Type 14, 15): Cr (customer paid us)
        - Payment (Type 3, 4): Dr (we paid them / refund to customer)
        - Debit Note (Type 1): Cr (reduces debtor balance)
        - Credit Note (Type 10): Dr (increases debtor balance)
        - Contra/Journal (Type 16, 19): Use Value1 sign
        
        Args:
            vch_type: Voucher type code
            value1: Signed amount from Tran2.Value1
            
        Returns:
            True for Dr, False for Cr
        """
        if self._is_credit_note_series(vch_type, vch_no):
            return False  # Cr

        # For Contra and Journal, use Value1 sign
        if vch_type in (VoucherType.CONTRA, VoucherType.JOURNAL):
            if value1 is not None:
                return value1 < 0  # Negative = Dr, Positive = Cr
            return True  # Default to Dr if no Value1
        
        # For known voucher types, use business logic
        if vch_type == VoucherType.SALES:
            return True  # Dr
        elif vch_type == VoucherType.PURCHASE:
            return False  # Cr
        elif vch_type in (VoucherType.RECEIPT, VoucherType.RECEIPT_ALT):
            return False  # Cr
        elif vch_type in (VoucherType.PAYMENT_CASH, VoucherType.PAYMENT_BANK):
            return True  # Dr
        elif vch_type == VoucherType.DEBIT_NOTE:
            return False  # Cr
        elif vch_type == VoucherType.CREDIT_NOTE:
            return True  # Dr
        else:
            # Unknown type - try Value1 or default to Dr
            if value1 is not None:
                return value1 < 0
            return True

    def _signed_contribution(self, vch_type: int, value1: Decimal, vch_no: Optional[str] = None) -> Decimal:
        """
        Convert a Tran2 row into signed debtor-balance movement.

        Positive increases Dr/receivable, negative increases Cr/payable.
        """
        if self._is_credit_note_series(vch_type, vch_no):
            return -abs(value1)
        if vch_type in (VoucherType.CONTRA, VoucherType.JOURNAL):
            return -value1
        if vch_type == VoucherType.SALES:
            return -value1
        if vch_type in (
            VoucherType.PAYMENT_CASH,
            VoucherType.PAYMENT_BANK,
            VoucherType.CREDIT_NOTE,
        ):
            return abs(value1)
        if vch_type in (
            VoucherType.PURCHASE,
            VoucherType.RECEIPT,
            VoucherType.RECEIPT_ALT,
            VoucherType.DEBIT_NOTE,
        ):
            return -abs(value1)
        return -value1

    def _classify_voucher_rows(
        self,
        vch_type: int,
        values: List[Decimal],
        vch_no: Optional[str] = None,
    ) -> Tuple[Decimal, bool]:
        """
        Collapse all party-linked Tran2 rows for a voucher into one effect.

        This keeps amount and Dr/Cr derived from the same canonical movement
        instead of an arbitrary fetch-one row.
        """
        if not values:
            return Decimal("0"), True

        net_effect = sum(
            (self._signed_contribution(vch_type, value, vch_no=vch_no) for value in values),
            Decimal("0"),
        )
        return abs(net_effect), net_effect >= 0
    
    def _select_best_counter_account(self, account_names: List[str]) -> str:
        """
        Select the most meaningful counter account from a list.
        
        Priority:
        1. Bank/Cash accounts
        2. Sales accounts
        3. Purchase accounts
        4. Any non-rounding account
        5. First available
        
        Args:
            account_names: List of account names
            
        Returns:
            Best account name or default
        """
        if not account_names:
            return DEFAULT_COUNTER_ACCOUNT
        
        # Priority 1: Bank/Cash accounts
        for name in account_names:
            if any(keyword in name.upper() for keyword in BANK_KEYWORDS):
                return name
        
        # Priority 2: Sales accounts
        for name in account_names:
            if any(keyword in name.upper() for keyword in SALES_KEYWORDS):
                if not any(r_keyword in name.upper() for r_keyword in ROUNDING_KEYWORDS):
                    return name
        
        # Priority 3: Purchase accounts
        for name in account_names:
            if any(keyword in name.upper() for keyword in PURCHASE_KEYWORDS):
                if not any(r_keyword in name.upper() for r_keyword in ROUNDING_KEYWORDS):
                    return name
        
        # Priority 4: Any non-rounding account
        for name in account_names:
            if not any(r_keyword in name.upper() for r_keyword in ROUNDING_KEYWORDS):
                return name
        
        # Fallback: first available
        return account_names[0]
    
    def _build_counter_account_lookup(
        self,
        vch_codes: List[int],
        party_code: int,
        cursor
    ) -> Dict[int, str]:
        """
        Build lookup mapping voucher codes to counter account names.
        
        Uses batch queries for efficiency.
        """
        if not vch_codes:
            return {}
        
        try:
            vch_list = ','.join(str(v) for v in vch_codes)
            
            # Get all Tran2 records for these vouchers
            cursor.execute(f"""
                SELECT 
                    VchCode,
                    MasterCode1,
                    RecType,
                    Value1,
                    SrNo
                FROM Tran2
                WHERE VchCode IN ({vch_list})
                    AND RecType = {RecType.MAIN_ACCOUNTING}
                ORDER BY VchCode, SrNo
            """)
            
            # Group by voucher code
            voucher_accounts: Dict[int, List[Dict]] = {}
            counter_codes: set = set()
            
            for row in cursor.fetchall():
                vch_code = row[0]
                mc1 = row[1]
                value1 = row[3]
                
                # Skip rounding entries (Value1 = 0)
                if value1 == 0:
                    continue
                
                # Skip if this is the party itself
                is_party_row = (mc1 == party_code)
                
                if not is_party_row and mc1:
                    if vch_code not in voucher_accounts:
                        voucher_accounts[vch_code] = []
                    voucher_accounts[vch_code].append({'code': mc1})
                    counter_codes.add(mc1)
            
            if not counter_codes:
                return {vch: DEFAULT_COUNTER_ACCOUNT for vch in vch_codes}
            
            # Batch lookup all account names
            code_list = ','.join(str(c) for c in counter_codes)
            cursor.execute(f"""
                SELECT Code, Name
                FROM Master1
                WHERE Code IN ({code_list})
            """)
            
            name_lookup: Dict[int, str] = {
                row[0]: row[1] for row in cursor.fetchall() if row[1]
            }
            
            # Build final lookup
            result: Dict[int, str] = {}
            for vch_code in vch_codes:
                if vch_code not in voucher_accounts:
                    result[vch_code] = DEFAULT_COUNTER_ACCOUNT
                    continue
                
                account_names = [
                    name_lookup.get(acc['code'], "")
                    for acc in voucher_accounts[vch_code]
                    if name_lookup.get(acc['code'], "")
                ]
                
                counter_name = self._select_best_counter_account(account_names)
                result[vch_code] = counter_name if counter_name else DEFAULT_COUNTER_ACCOUNT
            
            return result
            
        except Exception as e:
            logger.error("build_counter_lookup_error", error=str(e))
            return {vch: DEFAULT_COUNTER_ACCOUNT for vch in vch_codes}

    def _build_voucher_rows_lookup(
        self,
        vch_codes: List[int],
        cursor,
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Fetch all main accounting rows for the provided vouchers."""
        if not vch_codes:
            return {}

        try:
            vch_list = ",".join(str(v) for v in vch_codes)
            cursor.execute(f"""
                SELECT VchCode, SrNo, MasterCode1, MasterCode2, Value1
                FROM Tran2
                WHERE VchCode IN ({vch_list})
                  AND RecType = {RecType.MAIN_ACCOUNTING}
                ORDER BY VchCode, SrNo
            """)

            result: Dict[int, List[Dict[str, Any]]] = {}
            for row in cursor.fetchall():
                result.setdefault(int(row[0]), []).append(
                    {
                        "sr_no": int(row[1] or 0),
                        "master_code1": int(row[2] or 0),
                        "master_code2": int(row[3] or 0),
                        "value1": Decimal(str(row[4] or 0)),
                    }
                )
            return result
        except Exception as e:
            logger.error("build_voucher_rows_lookup_error", error=str(e))
            return {}

    def _build_master_name_lookup(
        self,
        master_codes: List[int],
        cursor,
    ) -> Dict[int, str]:
        """Resolve master codes to names in one batch."""
        codes = sorted({code for code in master_codes if code})
        if not codes:
            return {}

        try:
            code_list = ",".join(str(c) for c in codes)
            cursor.execute(f"""
                SELECT Code, Name
                FROM Master1
                WHERE Code IN ({code_list})
            """)
            return {int(row[0]): str(row[1]) for row in cursor.fetchall() if row[1]}
        except Exception as e:
            logger.error("build_master_name_lookup_error", error=str(e))
            return {}

    def _build_split_entries_for_voucher(
        self,
        *,
        vch_code: int,
        vch_date: date,
        vch_no: str,
        vch_type: int,
        party_code: int,
        voucher_rows_lookup: Dict[int, List[Dict[str, Any]]],
        master_name_lookup: Dict[int, str],
    ) -> Optional[List[LedgerEntry]]:
        """
        Split vouchers that contain multiple party-impact rows with mixed signs.

        Busy can encode a sale and an immediate settlement inside one voucher.
        Those vouchers must be expanded into separate ledger entries rather than
        collapsed into one absolute total.
        """
        detail_rows = voucher_rows_lookup.get(vch_code, [])
        if not detail_rows:
            return None

        party_rows = [
            row for row in detail_rows
            if row["value1"] != 0
            and (row["master_code1"] == party_code or row["master_code2"] == party_code)
        ]
        if len(party_rows) < 2:
            return None

        signs = {1 if row["value1"] > 0 else -1 for row in party_rows if row["value1"] != 0}
        if len(signs) < 2:
            return None

        split_entries: List[LedgerEntry] = []
        for party_row in party_rows:
            is_debit = party_row["value1"] < 0
            opposite_names: List[str] = []
            for row in detail_rows:
                if row["value1"] == 0:
                    continue
                is_party_row = row["master_code1"] == party_code or row["master_code2"] == party_code
                if is_party_row:
                    continue
                if row["value1"] * party_row["value1"] >= 0:
                    continue
                code = row["master_code1"] or row["master_code2"]
                name = master_name_lookup.get(code, "")
                if name:
                    opposite_names.append(name)

            particulars = self._select_best_counter_account(opposite_names)
            if vch_no:
                particulars = f"{particulars}-{vch_no.strip()}"

            split_voucher_type = self._get_voucher_type_name(vch_type, vch_no=vch_no)
            if vch_type == VoucherType.SALES and not is_debit:
                split_voucher_type = VOUCHER_TYPE_NAMES[VoucherType.RECEIPT]

            split_entries.append(
                LedgerEntry(
                    date=vch_date,
                    particulars=particulars,
                    voucher_no=vch_no,
                    voucher_type=split_voucher_type,
                    amount=abs(party_row["value1"]),
                    is_debit=is_debit,
                    balance=Decimal("0"),
                    narration=None,
                )
            )

        return split_entries or None
    
    def _build_voucher_effect_lookup(
        self,
        vch_codes: List[int],
        party_code: int,
        cursor
    ) -> Dict[int, Tuple[Decimal, bool]]:
        """
        Build lookup mapping voucher codes to canonical amount and Dr/Cr.
        """
        if not vch_codes:
            return {}
        
        try:
            vch_list = ','.join(str(v) for v in vch_codes)
            
            cursor.execute(f"""
                SELECT 
                    Tran2.VchCode,
                    Tran1.VchType,
                    Tran1.VchNo,
                    Tran2.Value1
                FROM Tran2
                INNER JOIN Tran1 ON Tran1.VchCode = Tran2.VchCode
                WHERE Tran2.VchCode IN ({vch_list})
                    AND (Tran2.MasterCode1 = {party_code} OR Tran2.MasterCode2 = {party_code})
                    AND Tran2.RecType = {RecType.MAIN_ACCOUNTING}
                    AND (Tran1.Cancelled = 0 OR Tran1.Cancelled IS NULL)
            """)
            
            rows_by_voucher: Dict[int, Dict[str, Any]] = {}
            for row in cursor.fetchall():
                vch_code = row[0]
                vch_type = int(row[1] or 0)
                vch_no = row[2]
                value1 = row[3]
                if value1 is not None:
                    bucket = rows_by_voucher.setdefault(
                        vch_code,
                        {"vch_type": vch_type, "vch_no": vch_no, "values": []},
                    )
                    bucket["values"].append(Decimal(str(value1)))

            result: Dict[int, Tuple[Decimal, bool]] = {}
            for vch_code, payload in rows_by_voucher.items():
                result[vch_code] = self._classify_voucher_rows(
                    payload["vch_type"],
                    payload["values"],
                    vch_no=payload.get("vch_no"),
                )

            return result
            
        except Exception as e:
            logger.error("build_voucher_effect_lookup_error", error=str(e))
            return {}
    
    def get_transactions(
        self,
        party_code: str,
        start_date: date,
        end_date: date,
        company_id: str = "default"
    ) -> List[LedgerEntry]:
        """
        Fetch all transactions for a party within date range.
        
        Args:
            party_code: Party code
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of LedgerEntry objects
            
        Raises:
            NoTransactionsError: If no transactions found
        """
        party_code_int = self._validate_party_code(party_code)
        
        try:
            with self.db.get_cursor(company_id=company_id) as cursor:
                # Find all voucher codes where party appears
                cursor.execute(f"""
                    SELECT DISTINCT VchCode 
                    FROM Tran2 
                    WHERE MasterCode1 = {party_code_int} OR MasterCode2 = {party_code_int}
                """)
                
                vch_codes = [row[0] for row in cursor.fetchall()]
                
                if not vch_codes:
                    logger.info(
                        "transactions_fetched",
                        party_code=party_code,
                        count=0,
                    )
                    return []
                
                logger.info("found_vouchers_in_tran2", party_code=party_code, count=len(vch_codes))
                
                # Get voucher headers
                vch_list = ','.join(str(v) for v in vch_codes)
                
                query = f"""
                    SELECT 
                        VchCode, Date, VchNo, VchType, VchAmtBaseCur, MasterCode1, MasterCode2
                    FROM Tran1
                    WHERE VchCode IN ({vch_list})
                        AND Date >= #{start_date.strftime('%m/%d/%Y')}#
                        AND Date <= #{end_date.strftime('%m/%d/%Y')}#
                        AND (Cancelled = 0 OR Cancelled IS NULL)
                    ORDER BY Date, VchCode
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                if not rows:
                    logger.info(
                        "transactions_fetched",
                        party_code=party_code,
                        count=0,
                    )
                    return []
                
                # Build batch lookups
                vch_codes_list = [row[0] for row in rows]
                counter_lookup = self._build_counter_account_lookup(
                    vch_codes_list, party_code_int, cursor
                )
                voucher_rows_lookup = self._build_voucher_rows_lookup(vch_codes_list, cursor)
                master_codes: List[int] = []
                for rows_for_voucher in voucher_rows_lookup.values():
                    for detail_row in rows_for_voucher:
                        if detail_row["master_code1"] != party_code_int:
                            master_codes.append(detail_row["master_code1"])
                        if detail_row["master_code2"] != party_code_int:
                            master_codes.append(detail_row["master_code2"])
                master_name_lookup = self._build_master_name_lookup(master_codes, cursor)
                effect_lookup = self._build_voucher_effect_lookup(
                    vch_codes_list, party_code_int, cursor
                )
                
                # Build entries
                entries: List[LedgerEntry] = []
                
                for row in rows:
                    vch_code = row[0]
                    vch_date = self._parse_date(row[1])
                    vch_no = row[2]
                    vch_type = row[3]
                    split_entries = self._build_split_entries_for_voucher(
                        vch_code=vch_code,
                        vch_date=vch_date,
                        vch_no=vch_no,
                        vch_type=vch_type,
                        party_code=party_code_int,
                        voucher_rows_lookup=voucher_rows_lookup,
                        master_name_lookup=master_name_lookup,
                    )
                    if split_entries:
                        entries.extend(split_entries)
                        continue
                    amount, is_debit = effect_lookup.get(
                        vch_code,
                        (
                            Decimal(str(abs(row[4] or 0))),
                            self._determine_dr_cr(vch_type, None, vch_no=vch_no),
                        ),
                    )
                    particulars = counter_lookup.get(vch_code, DEFAULT_COUNTER_ACCOUNT)
                    
                    # Append voucher number for sales invoices using dash to prevent wrapping
                    if vch_type == VoucherType.SALES and vch_no:
                        particulars = f"{particulars}-{vch_no}"
                    
                    entries.append(LedgerEntry(
                        date=vch_date,
                        particulars=particulars,
                        voucher_no=vch_no,
                        voucher_type=self._get_voucher_type_name(vch_type, vch_no=vch_no),
                        amount=amount,
                        is_debit=is_debit,
                        balance=Decimal('0'),  # Will be calculated later
                        narration=None
                    ))
                
                logger.info("transactions_fetched", party_code=party_code, count=len(entries))
                return entries
                
        except NoTransactionsError:
            raise
        except Exception as e:
            logger.error("get_transactions_error", company_id=company_id, party_code=party_code, error=str(e))
            raise NoTransactionsError(
                party_code=party_code,
                start_date=str(start_date),
                end_date=str(end_date),
                message=f"Error: {str(e)}"
            ) from e
    
    def calculate_balances(
        self,
        opening_balance: Decimal,
        entries: List[LedgerEntry]
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate running balances and totals for all entries.
        
        Business Logic (from Business POV):
        - Opening Dr balance: We owe them / they owe us (positive = liability)
        - Dr entries: Increase Dr balance (sales, payments to them)
        - Cr entries: Decrease Dr balance (receipts from them, purchases)
        - Running balance: Opening - Dr + Cr (for Dr opening)
        
        Args:
            opening_balance: Opening balance (positive = Cr, negative = Dr)
            entries: List of entries (modified in-place)
            
        Returns:
            Tuple of (total_debits, total_credits)
        """
        running_balance = opening_balance
        total_debits = Decimal('0')
        total_credits = Decimal('0')
        
        for entry in entries:
            if entry.is_debit:
                # Dr = Sales = Customer owes us more (INCREASE Dr balance)
                running_balance += entry.amount
                total_debits += entry.amount
            else:
                # Cr = Receipts = Customer paid us (DECREASE Dr balance)
                running_balance -= entry.amount
                total_credits += entry.amount
            
            entry.balance = running_balance
        
        return total_debits, total_credits
    
    def generate_ledger_report(
        self,
        party_code: str,
        company_id: str = "default"
    ) -> LedgerReport:
        """
        Generate complete ledger report for a customer.
        
        Args:
            party_code: Party code
            
        Returns:
            LedgerReport with all data
            
        Raises:
            PartyNotFoundError: If party not found
            NoTransactionsError: If no transactions found
        """
        from datetime import datetime
        
        logger.info("generating_ledger_report", company_id=company_id, party_code=party_code)
        
        fy_info = self.get_financial_year(company_id=company_id)
        company = self.get_company_info(company_id=company_id)
        customer = self.get_customer_info(party_code, company_id=company_id)
        opening_balance = self.get_opening_balance(party_code, fy_info.start_date, company_id=company_id)
        
        entries = self.get_transactions(
            party_code,
            fy_info.start_date,
            fy_info.end_date,
            company_id=company_id
        )
        
        total_debits, total_credits = self.calculate_balances(opening_balance, entries)
        
        # Calculate closing balance
        closing_balance = opening_balance + total_debits - total_credits
        
        logger.info(
            "ledger_report_generated",
            party_code=party_code,
            entries_count=len(entries),
            opening_balance=opening_balance,
            closing_balance=closing_balance
        )
        
        return LedgerReport(
            company=company,
            customer=customer,
            financial_year=fy_info,
            generated_at=datetime.now(),
            opening_balance=opening_balance,
            entries=entries,
            closing_balance=closing_balance,
            total_debits=total_debits,
            total_credits=total_credits
        )

    def compute_party_balances_and_recent_sales(
        self,
        *,
        party_credit_days: Dict[int, int],
        as_of_date: Optional[date] = None,
        company_id: str = "default",
    ) -> Dict[int, Dict[str, Decimal]]:
        """
        Compute closing balances and recent-sales totals for many parties at once.

        This uses the same canonical sign rules as ledger reconstruction while
        avoiding one full ODBC connection cycle per party.
        """
        if as_of_date is None:
            as_of_date = date.today()
        if not party_credit_days:
            return {}

        party_codes = sorted(party_credit_days.keys())
        party_code_set = set(party_codes)
        cutoff_map = {
            code: as_of_date - timedelta(days=int(party_credit_days[code]))
            for code in party_codes
        }
        closing_map: Dict[int, Decimal] = {code: Decimal("0") for code in party_codes}
        recent_sales_map: Dict[int, Decimal] = {code: Decimal("0") for code in party_codes}
        seen_sales_vouchers: Set[Tuple[int, int]] = set()

        # Parent groups for opening-balance normalization.
        for i in range(0, len(party_codes), 500):
            chunk = party_codes[i:i + 500]
            in_clause = ",".join(str(c) for c in chunk)
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute(f"""
                    SELECT Code, ParentGrp
                    FROM Master1
                    WHERE MasterType = {MasterType.PARTY}
                      AND Code IN ({in_clause})
                """)
                parent_groups = {int(row[0]): int(row[1] or 0) for row in cursor.fetchall()}

                cursor.execute(f"""
                    SELECT MasterCode, D1
                    FROM Folio1
                    WHERE MasterType = {MasterType.PARTY}
                      AND MasterCode IN ({in_clause})
                """)
                for row in cursor.fetchall():
                    code = int(row[0])
                    raw = Decimal(str(row[1] or 0))
                    closing_map[code] = self._normalize_opening_balance_for_parent_group(
                        raw,
                        parent_groups.get(code),
                    )

        fy = self.get_financial_year(company_id=company_id)
        start_s = fy.start_date.strftime("%m/%d/%Y")
        end_s = fy.end_date.strftime("%m/%d/%Y")

        for i in range(0, len(party_codes), 500):
            chunk = party_codes[i:i + 500]
            chunk_set = set(chunk)
            in_clause = ",".join(str(c) for c in chunk)
            with self.db.get_cursor(company_id=company_id) as cursor:
                cursor.execute(f"""
                    SELECT
                        t2.VchCode,
                        t2.MasterCode1,
                        t2.MasterCode2,
                        t2.Value1,
                        t1.VchType,
                        t1.VchNo,
                        t1.Date,
                        t1.VchAmtBaseCur
                    FROM Tran2 t2
                    INNER JOIN Tran1 t1 ON t1.VchCode = t2.VchCode
                    WHERE t2.RecType = {RecType.MAIN_ACCOUNTING}
                      AND t1.Date >= #{start_s}#
                      AND t1.Date <= #{end_s}#
                      AND (t1.Cancelled = 0 OR t1.Cancelled IS NULL)
                      AND (t2.MasterCode1 IN ({in_clause}) OR t2.MasterCode2 IN ({in_clause}))
                    ORDER BY t1.Date, t2.VchCode, t2.SrNo
                """)

                for row in cursor.fetchall():
                    vch_code = int(row[0] or 0)
                    mc1 = int(row[1] or 0)
                    mc2 = int(row[2] or 0)
                    value1 = Decimal(str(row[3] or 0))
                    vch_type = int(row[4] or 0)
                    vch_no = row[5]
                    vdate = self._parse_date(row[6])
                    vamt = Decimal(str(row[7] or 0))

                    party_code = mc1 if mc1 in chunk_set else (mc2 if mc2 in chunk_set else 0)
                    if not party_code or party_code not in party_code_set:
                        continue

                    signed = self._signed_contribution(vch_type, value1, vch_no=vch_no)
                    closing_map[party_code] += signed

                    if vch_type == VoucherType.SALES and signed > 0:
                        sale_key = (party_code, vch_code)
                        if sale_key not in seen_sales_vouchers and cutoff_map[party_code] <= vdate <= as_of_date:
                            seen_sales_vouchers.add(sale_key)
                            recent_sales_map[party_code] += vamt

        return {
            code: {
                "closing_balance": closing_map.get(code, Decimal("0")),
                "recent_sales_total": recent_sales_map.get(code, Decimal("0")),
                "amount_due": closing_map.get(code, Decimal("0")) - recent_sales_map.get(code, Decimal("0")),
            }
            for code in party_codes
        }


# Global instance for convenience
ledger_data_service = LedgerDataService()
