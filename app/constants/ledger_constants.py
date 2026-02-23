"""
Constants and configuration for ledger generation.
All magic numbers and business rules centralized here.
"""
from enum import IntEnum
from typing import Dict


class RecType(IntEnum):
    """Record types in Busy database."""
    MAIN_ACCOUNTING = 1
    ITEM_DETAILS = 2
    ROUNDING = 3


class MasterType(IntEnum):
    """Master account types in Busy database."""
    ACCOUNT = 1
    PARTY = 2  # Customers, Suppliers
    ITEM = 3
    # Additional types may vary by Busy version


class VoucherType(IntEnum):
    """Voucher types in Busy database."""
    DEBIT_NOTE = 1
    PURCHASE = 2  # SupI
    PAYMENT_CASH = 3
    PAYMENT_BANK = 4
    # Type 5-8 may vary
    SALES = 9  # SupO
    CREDIT_NOTE = 10
    # Type 11-13 may vary
    RECEIPT = 14
    RECEIPT_ALT = 15
    CONTRA = 16
    # Type 17-18 may vary
    JOURNAL = 19


class ConfigRecType(IntEnum):
    """Config table record types for system settings."""
    # These may vary by Busy version/customization
    FINANCIAL_YEAR = 7
    COMPANY_INFO = 8


# Voucher type display names
VOUCHER_TYPE_NAMES: Dict[int, str] = {
    VoucherType.SALES: "SupO",
    VoucherType.PURCHASE: "SupI", 
    VoucherType.PAYMENT_CASH: "Pymt",
    VoucherType.PAYMENT_BANK: "Pymt",
    VoucherType.RECEIPT: "Rcpt",
    VoucherType.RECEIPT_ALT: "Rcpt",
    VoucherType.CONTRA: "Contra",
    VoucherType.JOURNAL: "Jrnl",
    VoucherType.DEBIT_NOTE: "DrNt",
    VoucherType.CREDIT_NOTE: "CrNt",
}

# Bank/Cash account keywords for counter account prioritization
# These are used to identify bank accounts in the counter party selection
BANK_KEYWORDS = [
    'BANK',
    'CASH', 
    'CC A/C',
    'HDFC',
    'PNB',
    'SBI',
    'AXIS',
    'ICICI',
    'BOB',
    'UBI',
    'CANARA',
    'UNION',
    'IDBI',
    'IOB',
    'CBI',
    'OBC',
    'SBBJ',
    'SBH',
    'SBM',
    'SBT',
    'SYNDICATE',
    'VIJAYA',
    'DENA',
    'ANDHRA',
    'CORPORATION',
    'INDIAN',
    'ALLAHABAD',
    'CENTRAL',
    'BOM',
    'BNP',
    'CITI',
    'HSBC',
    'STANCHART',
    'YES',
    'KOTAK',
    'INDUSIND',
    'FEDERAL',
    'RBL',
    'BANDHAN',
    'IDFC',
]

# Account type keywords for counter account selection
SALES_KEYWORDS = ['SALE', 'SALES']
PURCHASE_KEYWORDS = ['PURCHASE', 'PURCH']
ROUNDING_KEYWORDS = ['ROUND', 'ROUNDING']

# Default fallback values - should be minimal and generic
DEFAULT_COUNTER_ACCOUNT = "Transaction"
DEFAULT_FONT_FAMILY = "Arial"

# PDF Layout Constants
PDF_PAGE_WIDTH = 210  # A4 width in mm
PDF_PAGE_HEIGHT = 297  # A4 height in mm
PDF_MARGIN_LEFT = 15
PDF_MARGIN_RIGHT = 15
PDF_MARGIN_TOP = 10
PDF_MARGIN_BOTTOM = 10

# Date formats used for parsing
DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y", 
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%m/%d/%Y",  # US format for Access
]

# Maximum length for particulars truncation in PDF
MAX_PARTICULARS_LENGTH = 50

# Decimal precision for financial calculations
DECIMAL_PRECISION = 2

# File paths and extensions
PDF_EXTENSION = ".pdf"
TEMP_FILE_PREFIX = "ledger_"
