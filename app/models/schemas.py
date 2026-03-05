from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InvoiceNotification(BaseModel):
    """Schema for invoice notification from Busy."""
    phone: str = Field(..., description="Customer phone number")
    msg: str = Field(..., description="Message text")
    pdf_url: Optional[str] = Field(None, description="URL to invoice PDF")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+919876543210",
                "msg": "Your invoice #INV001 for Rs. 5000 is ready",
                "pdf_url": "https://bdep.busy.in/invoice/12345.pdf"
            }
        }


class PartyDetails(BaseModel):
    """Schema for party/account details from Master1."""
    code: str = Field(..., description="Party code")
    name: str = Field(..., description="Party name")
    print_name: Optional[str] = Field(None, description="Display name")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    address1: Optional[str] = Field(None, description="Address line 1")
    address2: Optional[str] = Field(None, description="Address line 2")
    address3: Optional[str] = Field(None, description="Address line 3")
    address4: Optional[str] = Field(None, description="Address line 4")
    gst_no: Optional[str] = Field(None, description="GST number")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "C001",
                "name": "ABC Enterprises",
                "print_name": "ABC Enterprises Pvt Ltd",
                "phone": "+919876543210",
                "email": "contact@abc.com",
                "address1": "123 Main Street",
                "address2": "Mumbai",
                "address3": "Maharashtra",
                "address4": "400001",
                "gst_no": "27AABCU9603R1ZM"
            }
        }


class VoucherDetails(BaseModel):
    """Schema for voucher details from Tran1."""
    vch_code: int = Field(..., description="Voucher code")
    vch_type: str = Field(..., description="Voucher type")
    vch_no: str = Field(..., description="Voucher number")
    vch_date: datetime = Field(..., description="Voucher date")
    party_code: str = Field(..., description="Party code")
    amount: Optional[float] = Field(None, description="Total amount")
    narration: Optional[str] = Field(None, description="Narration")
    
    class Config:
        json_schema_extra = {
            "example": {
                "vch_code": 12345,
                "vch_type": "Sales",
                "vch_no": "INV-001",
                "vch_date": "2024-02-18T10:30:00",
                "party_code": "C001",
                "amount": 5000.00,
                "narration": "Sales Invoice"
            }
        }


class WhatsAppMessage(BaseModel):
    """Schema for WhatsApp message request."""
    to: str = Field(..., description="Recipient phone number")
    body: str = Field(..., description="Message body")
    media_url: Optional[str] = Field(None, description="Media/PDF URL")
    file_name: Optional[str] = Field(None, description="Media filename for WhatsApp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "to": "+919876543210",
                "body": "Your invoice is ready",
                "media_url": "https://example.com/invoice.pdf",
                "file_name": "abc_enterprises_invoice_05-03-2026.pdf"
            }
        }


class WhatsAppResponse(BaseModel):
    """Schema for WhatsApp message response."""
    success: bool = Field(..., description="Whether message was sent successfully")
    message_id: Optional[str] = Field(None, description="Message ID from provider")
    delivery_status: Optional[str] = Field(None, description="Provider delivery status")
    normalized_to: Optional[str] = Field(None, description="Normalized destination number")
    contact_name: Optional[str] = Field(None, description="Resolved contact/display name if available")
    contact_source: Optional[str] = Field(None, description="Source of contact metadata")
    contact_is_saved: Optional[bool] = Field(None, description="Whether contact is saved in address book")
    contact_state: Optional[str] = Field(None, description="saved|likely_unsaved|unknown|not_on_whatsapp")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message_id": "SM1234567890",
                "error": None
            }
        }


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    database_connected: bool = Field(..., description="Database connectivity status")
    timestamp: datetime = Field(..., description="Current timestamp")
    whatsapp: dict = Field(default_factory=dict, description="WhatsApp provider status")
