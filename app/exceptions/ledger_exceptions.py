"""
Custom exceptions for ledger PDF generation.

These exceptions provide specific error codes that the payment reminder system
can use to determine appropriate action.
"""
from typing import Optional


class LedgerError(Exception):
    """Base exception for ledger-related errors."""
    
    error_code: str = "LEDGER_ERROR"
    message: str = "An error occurred while generating the ledger"
    
    def __init__(self, message: Optional[str] = None, details: Optional[dict] = None):
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class CompanyInfoError(LedgerError):
    """Raised when company details cannot be found in Config table."""
    
    error_code = "COMPANY_INFO_MISSING"
    message = "Company details not found in Config table (RecType 8)"


class FinancialYearError(LedgerError):
    """Raised when financial year cannot be determined."""
    
    error_code = "FINANCIAL_YEAR_ERROR"
    message = "Could not determine financial year from database"


class PartyNotFoundError(LedgerError):
    """Raised when the specified party/customer is not found."""
    
    error_code = "PARTY_NOT_FOUND"
    message = "Customer not found in Master1"
    
    def __init__(self, party_code: str, message: Optional[str] = None):
        super().__init__(
            message=message or f"Party with code '{party_code}' not found",
            details={"party_code": party_code}
        )


class NoTransactionsError(LedgerError):
    """Raised when no transactions exist for the party in the date range."""
    
    error_code = "NO_TRANSACTIONS"
    message = "No transactions found for specified date range"
    
    def __init__(self, party_code: str, start_date: str, end_date: str, message: Optional[str] = None):
        super().__init__(
            message=message or f"No transactions found for party {party_code}",
            details={
                "party_code": party_code,
                "start_date": start_date,
                "end_date": end_date
            }
        )


class OpeningBalanceError(LedgerError):
    """Raised when opening balance cannot be determined."""
    
    error_code = "OPENING_BALANCE_ERROR"
    message = "Could not calculate opening balance"


class PDFGenerationError(LedgerError):
    """Raised when PDF generation fails unexpectedly."""
    
    error_code = "PDF_GENERATION_FAILED"
    message = "Failed to generate PDF"


class DatabaseConnectionError(LedgerError):
    """Raised when database connection fails."""
    
    error_code = "DATABASE_CONNECTION_ERROR"
    message = "Could not connect to database"
