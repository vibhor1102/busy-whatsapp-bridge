"""
Pydantic schemas for ledger data structures.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

from app.utils.number_format import format_indian_number


class FinancialYearInfo(BaseModel):
    """Financial year information from database."""
    start_date: date
    end_date: date
    year_name: str = Field(..., description="e.g., '2025-26'")


class CompanyInfo(BaseModel):
    """Company details for PDF header."""
    name: str
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    address_line3: Optional[str] = None
    address_line4: Optional[str] = None
    gst_no: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class CustomerInfo(BaseModel):
    """Customer/Party details."""
    code: str
    name: str
    print_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    address_line3: Optional[str] = None
    address_line4: Optional[str] = None
    gst_no: Optional[str] = None
    phone: Optional[str] = None


class LedgerEntry(BaseModel):
    """Single ledger transaction entry."""
    date: date
    particulars: str
    voucher_no: str
    voucher_type: str
    amount: Decimal
    is_debit: bool  # True = Dr, False = Cr
    balance: Decimal  # Running balance
    narration: Optional[str] = None
    
    @property
    def amount_formatted(self) -> str:
        """Format amount with Dr/Cr suffix."""
        suffix = " Dr" if self.is_debit else " Cr"
        return f"{format_indian_number(self.amount)}{suffix}"
    
    @property
    def balance_formatted(self) -> str:
        """Format balance with Dr/Cr suffix."""
        # Positive balance = Dr (customer owes us - receivable)
        # Negative balance = Cr (we owe customer - payable)
        amount = abs(self.balance)
        suffix = " Dr" if self.balance >= 0 else " Cr"
        return f"{format_indian_number(amount)}{suffix}"
    
    @property
    def date_formatted(self) -> str:
        """Format date as DD/MM/YYYY."""
        return self.date.strftime("%d/%m/%Y")


class LedgerReport(BaseModel):
    """Complete ledger report data."""
    company: CompanyInfo
    customer: CustomerInfo
    financial_year: FinancialYearInfo
    generated_at: datetime
    opening_balance: Decimal
    entries: List[LedgerEntry]
    closing_balance: Decimal
    total_debits: Decimal
    total_credits: Decimal
    
    @property
    def opening_balance_formatted(self) -> str:
        """Format opening balance with Dr/Cr suffix."""
        # Positive = Dr (customer owes us), Negative = Cr (we owe customer)
        amount = abs(self.opening_balance)
        suffix = " Dr" if self.opening_balance >= 0 else " Cr"
        return f"{format_indian_number(amount)}{suffix}"
    
    @property
    def closing_balance_formatted(self) -> str:
        """Format closing balance with Dr/Cr suffix."""
        # Positive = Dr (customer owes us), Negative = Cr (we owe customer)
        amount = abs(self.closing_balance)
        suffix = " Dr" if self.closing_balance >= 0 else " Cr"
        return f"{format_indian_number(amount)}{suffix}"
    
    @property
    def total_debits_formatted(self) -> str:
        return format_indian_number(self.total_debits)
    
    @property
    def total_credits_formatted(self) -> str:
        return format_indian_number(self.total_credits)


class LedgerGenerationRequest(BaseModel):
    """Request to generate a ledger PDF."""
    party_code: str = Field(..., description="Customer code from Master1")
    output_path: Optional[str] = Field(None, description="Optional output path (temp file if not provided)")
