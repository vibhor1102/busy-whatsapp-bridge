"""
Pydantic schemas for ledger data structures.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal


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
        return f"{self.amount:,.2f}{suffix}"
    
    @property
    def balance_formatted(self) -> str:
        """Format balance with Dr/Cr suffix."""
        # Positive balance = Cr (customer owes us or has credit)
        # Negative balance = Dr (we owe customer)
        amount = abs(self.balance)
        suffix = " Cr" if self.balance >= 0 else " Dr"
        return f"{amount:,.2f}{suffix}"
    
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
        amount = abs(self.opening_balance)
        suffix = " Cr" if self.opening_balance >= 0 else " Dr"
        return f"{amount:,.2f}{suffix}"
    
    @property
    def closing_balance_formatted(self) -> str:
        """Format closing balance with Dr/Cr suffix."""
        amount = abs(self.closing_balance)
        suffix = " Cr" if self.closing_balance >= 0 else " Dr"
        return f"{amount:,.2f}{suffix}"
    
    @property
    def total_debits_formatted(self) -> str:
        return f"{self.total_debits:,.2f}"
    
    @property
    def total_credits_formatted(self) -> str:
        return f"{self.total_credits:,.2f}"


class LedgerGenerationRequest(BaseModel):
    """Request to generate a ledger PDF."""
    party_code: str = Field(..., description="Customer code from Master1")
    output_path: Optional[str] = Field(None, description="Optional output path (temp file if not provided)")
