"""
Pydantic schemas for Payment Reminder System
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

from app.constants.reminder_constants import (
    DEFAULT_CREDIT_DAYS,
    DEFAULT_SCHEDULE_DAY,
    DEFAULT_SCHEDULE_ENABLED,
    DEFAULT_SCHEDULE_TIME,
    DEFAULT_SCHEDULE_TIMEZONE,
    SCHEDULE_FREQUENCY_WEEKLY,
    VALID_SCHEDULE_FREQUENCIES,
    TEMPLATE_VARIABLES,
    DEFAULT_TEMPLATE_ID,
)


class PartyReminderInfo(BaseModel):
    """Party information for reminder selection UI"""
    code: str = Field(..., description="Party code from Master1")
    name: str = Field(..., description="Party name")
    print_name: Optional[str] = Field(None, description="Print name for display")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Formatted address")
    
    # Financial info
    closing_balance: Decimal = Field(..., description="Closing balance from ledger")
    closing_balance_formatted: str = Field(..., description="Formatted closing balance")
    amount_due: Decimal = Field(..., description="Calculated amount due")
    amount_due_formatted: str = Field(..., description="Formatted amount due")
    
    # Credit info (from Master1)
    sales_credit_days: int = Field(default=DEFAULT_CREDIT_DAYS, description="Sales credit days from Master1.I2")
    purchase_credit_days: Optional[int] = Field(None, description="Purchase credit days from Master1.I1")
    credit_days_source: str = Field(default="config_default", description="Source of credit days value")
    
    # Reminder settings
    permanent_enabled: bool = Field(default=False, description="Permanent reminder setting from JSON config")
    temp_enabled: bool = Field(default=False, description="Temporary selection for current batch (session only)")
    
    # Metadata
    last_reminder_sent: Optional[datetime] = Field(None, description="Last reminder sent timestamp")
    reminder_count: int = Field(default=0, description="Total reminders sent to this party")
    
    # Actions
    can_generate_ledger: bool = Field(default=True, description="Whether ledger can be generated")


class AmountDueCalculation(BaseModel):
    """Detailed breakdown of amount due calculation"""
    party_code: str = Field(..., description="Party code")
    party_name: str = Field(..., description="Party name")
    
    closing_balance: Decimal = Field(..., description="Closing balance from ledger")
    credit_days_used: int = Field(..., description="Credit days used in calculation")
    credit_days_source: Literal["master1_i2", "config_default", "override"] = Field(
        ..., description="Source of credit days"
    )
    
    recent_sales_total: Decimal = Field(..., description="Sum of sales in credit period")
    recent_sales_count: int = Field(..., description="Number of sales transactions")
    recent_sales_date_range: Tuple[date, date] = Field(..., description="Date range of recent sales")
    
    amount_due: Decimal = Field(..., description="Final calculated amount due")
    calculation_timestamp: datetime = Field(default_factory=datetime.now, description="When calculation was performed")


class PartyConfig(BaseModel):
    """Per-party configuration (stored in JSON if different from default)"""
    enabled: bool = Field(default=False, description="Whether reminders are enabled for this party")
    credit_days_override: Optional[int] = Field(None, description="Override default credit days")
    custom_template_id: Optional[str] = Field(None, description="Custom template for this party")
    custom_message: Optional[str] = Field(None, description="Custom message override")
    notes: Optional[str] = Field(None, description="Internal notes about this party")
    
    @field_validator('credit_days_override')
    @classmethod
    def validate_credit_days(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 365):
            raise ValueError('Credit days must be between 1 and 365')
        return v


class ScheduleConfig(BaseModel):
    """Scheduler configuration"""
    enabled: bool = Field(default=DEFAULT_SCHEDULE_ENABLED, description="Whether scheduler is enabled")
    frequency: Literal["weekly", "biweekly"] = Field(
        default=SCHEDULE_FREQUENCY_WEEKLY, 
        description="Reminder frequency"
    )
    day_of_week: int = Field(
        default=DEFAULT_SCHEDULE_DAY, 
        ge=0, le=6,
        description="Day of week (0=Sunday, 6=Saturday)"
    )
    time: str = Field(default=DEFAULT_SCHEDULE_TIME, description="Time in 24-hour format (HH:MM)")
    timezone: str = Field(default=DEFAULT_SCHEDULE_TIMEZONE, description="Timezone for schedule")
    batch_size: int = Field(default=50, ge=10, le=500, description="Messages per batch")
    delay_between_messages: int = Field(default=5, ge=1, le=60, description="Seconds between API calls")
    
    @field_validator('time')
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError('Time must be in HH:MM format')
        return v


class LedgerSettings(BaseModel):
    """Ledger generation settings"""
    date_range_days: int = Field(default=90, ge=30, le=365, description="Days of transaction history to include")
    include_all_transactions: bool = Field(default=True, description="Include all transactions or only recent")


class HistorySettings(BaseModel):
    """Reminder history retention settings"""
    retention_days: int = Field(default=365, ge=30, le=1825, description="Days to keep reminder history")


class LimitsConfig(BaseModel):
    """System limits configuration"""
    max_templates: int = Field(default=6, ge=3, le=20, description="Maximum number of templates allowed")
    max_batch_size: int = Field(default=500, ge=50, le=1000, description="Maximum messages per batch")
    max_delay_between_messages: int = Field(default=60, ge=10, le=300, description="Maximum seconds between messages")


class CompanySettings(BaseModel):
    """Company information for reminders"""
    name: str = Field(default="Company", description="Company name used in templates")
    contact_phone: str = Field(default="", description="Contact phone number for customer queries")
    address: Optional[str] = Field(None, description="Company address")


class MessageTemplate(BaseModel):
    """Message template for reminders"""
    id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Display name for template")
    description: Optional[str] = Field(None, description="Description of when to use this template")
    content: str = Field(..., description="Template content with variables")
    variables: List[str] = Field(
        default_factory=lambda: TEMPLATE_VARIABLES.copy(),
        description="Available variables in template"
    )
    is_default: bool = Field(default=False, description="Whether this is the default template")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class ReminderConfig(BaseModel):
    """Root configuration stored in reminder_config.json"""
    version: str = Field(default="1.0", description="Config file version")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    
    # Global defaults
    default_credit_days: int = Field(
        default=DEFAULT_CREDIT_DAYS, 
        ge=1, le=365,
        description="Default credit days when Master1.I2 is 0"
    )
    # =============================================================================
    # NOTE: Changed default from "meta" to "baileys"
    # Only Baileys is now available - other providers removed.
    # TODO: Re-add via Baileys integration when needed
    # =============================================================================
    default_provider: str = Field(default="baileys", description="Default WhatsApp provider")
    currency_symbol: str = Field(default="₹", description="Currency symbol for formatting")
    
    # Company settings
    company: CompanySettings = Field(default_factory=lambda: CompanySettings(), description="Company information")
    
    # Scheduling
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig, description="Scheduler configuration")
    
    # Ledger settings
    ledger: LedgerSettings = Field(default_factory=LedgerSettings, description="Ledger generation settings")
    
    # History settings
    history: HistorySettings = Field(default_factory=HistorySettings, description="History retention settings")
    
    # System limits
    limits: LimitsConfig = Field(default_factory=LimitsConfig, description="System limits")
    
    # Party overrides (only stored if different from default)
    parties: Dict[str, PartyConfig] = Field(
        default_factory=dict, 
        description="Per-party configurations"
    )
    
    # Templates
    templates: List[MessageTemplate] = Field(
        default_factory=list, 
        description="Available message templates"
    )
    active_template_id: str = Field(
        default=DEFAULT_TEMPLATE_ID, 
        description="Currently active template ID"
    )


class ReminderBatch(BaseModel):
    """A batch of reminders being sent"""
    batch_id: str = Field(..., description="Unique batch identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled send time")
    sent_at: Optional[datetime] = Field(None, description="Actual send timestamp")
    
    template_id: str = Field(..., description="Template used for this batch")
    party_count: int = Field(..., description="Number of parties in batch")
    parties: List[str] = Field(..., description="List of party codes")
    
    status: Literal["draft", "scheduled", "sending", "completed", "failed", "cancelled"] = Field(
        default="draft", 
        description="Current batch status"
    )
    results: Optional[Dict[str, Any]] = Field(None, description="Per-party results after sending")


class ReminderHistory(BaseModel):
    """Record of sent reminders"""
    id: str = Field(..., description="Unique history record ID")
    party_code: str = Field(..., description="Party code")
    party_name: str = Field(..., description="Party name")
    
    batch_id: str = Field(..., description="Associated batch ID")
    sent_at: datetime = Field(..., description="When reminder was sent")
    sent_by: Literal["scheduler", "manual"] = Field(..., description="How reminder was triggered")
    
    template_id: str = Field(..., description="Template used")
    message_content: str = Field(..., description="Actual message content sent")
    amount_due: Decimal = Field(..., description="Amount due at time of sending")
    
    status: Literal["queued", "accepted", "sent", "delivered", "read", "failed"] = Field(
        ..., description="Message status"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    whatsapp_message_id: Optional[str] = Field(None, description="WhatsApp message ID from Meta")


class ReminderStats(BaseModel):
    """Reminder system statistics"""
    total_parties: int = Field(..., description="Total parties in database")
    eligible_parties: int = Field(..., description="Parties with amount_due > 0")
    enabled_parties: int = Field(..., description="Parties with permanent_enabled=True")
    
    reminders_sent_today: int = Field(..., description="Reminders sent today")
    reminders_sent_this_week: int = Field(..., description="Reminders sent this week")
    reminders_sent_this_month: int = Field(..., description="Reminders sent this month")
    
    total_amount_due: Decimal = Field(..., description="Sum of all amounts due")
    average_amount_due: Decimal = Field(..., description="Average amount due")
    
    last_scheduler_run: Optional[datetime] = Field(None, description="Last time scheduler ran")
    next_scheduler_run: Optional[datetime] = Field(None, description="Next scheduled run time")
    scheduler_status: Literal["running", "stopped", "paused"] = Field(..., description="Scheduler status")


class PartyListRequest(BaseModel):
    """Request body for listing parties"""
    search: Optional[str] = Field(None, description="Search term for party name/code")
    sort_by: Literal["amount_due", "name", "credit_days", "last_reminder", "code"] = Field(
        default="amount_due", 
        description="Sort field"
    )
    sort_order: Literal["asc", "desc"] = Field(default="desc", description="Sort order")
    filter_by: Literal["all", "enabled", "disabled", "never_reminded", "reminded_recently"] = Field(
        default="all", 
        description="Filter option"
    )
    min_amount_due: Optional[Decimal] = Field(None, description="Minimum amount due filter")


class PaginatedPartyReminderResponse(BaseModel):
    """Paginated response envelope for reminder parties."""
    items: List[PartyReminderInfo] = Field(default_factory=list)
    total: int = Field(default=0)
    offset: int = Field(default=0)
    limit: int = Field(default=100)
    has_more: bool = Field(default=False)


class ReminderSnapshotStatus(BaseModel):
    """Status of reminder snapshot storage."""
    has_snapshot: bool = Field(default=False)
    last_refreshed_at: Optional[datetime] = None
    duration_ms: int = Field(default=0)
    row_count: int = Field(default=0)
    nonzero_count: int = Field(default=0)
    error_count: int = Field(default=0)
    source_db_path_hash: Optional[str] = None


class RefreshStats(BaseModel):
    """Refresh statistics for progress tracking and staleness checks."""
    last_refresh_at: Optional[datetime] = Field(None, description="When data was last refreshed")
    last_5_durations_ms: List[int] = Field(default_factory=list, description="Last 5 refresh durations in ms")
    rolling_avg_ms: int = Field(default=0, description="Rolling average of last 5 refresh durations")
    last_reminder_sent_at: Optional[datetime] = Field(None, description="When reminders were last sent for this company")


class CreateBatchRequest(BaseModel):
    """Request body for creating a reminder batch"""
    party_codes: List[str] = Field(..., description="List of party codes to include")
    template_id: str = Field(..., description="Template to use")
    schedule_for: Optional[datetime] = Field(None, description="When to send (None = immediate)")
    party_templates: Optional[Dict[str, str]] = Field(
        None,
        description="Per-party template overrides: {party_code: template_id}"
    )

    @field_validator('party_codes')
    @classmethod
    def validate_party_codes(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError('party_codes cannot be empty')
        return v


class UpdatePartyRequest(BaseModel):
    """Request body for updating party configuration"""
    permanent_enabled: Optional[bool] = Field(None, description="Update permanent enabled status")
    credit_days_override: Optional[int] = Field(None, description="Override credit days")
    custom_template_id: Optional[str] = Field(None, description="Custom template")
    notes: Optional[str] = Field(None, description="Internal notes")
    
    @field_validator('credit_days_override')
    @classmethod
    def validate_credit_days(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 365):
            raise ValueError('Credit days must be between 1 and 365')
        return v


class PreviewTemplateRequest(BaseModel):
    """Request body for previewing a template"""
    template_id: str = Field(..., description="Template to preview")
    variables: Dict[str, str] = Field(default_factory=dict, description="Variable values for preview")


class SchedulerControlRequest(BaseModel):
    """Request body for scheduler control"""
    action: Literal["start", "stop", "pause", "resume", "trigger"] = Field(
        ..., 
        description="Action to perform"
    )


class ReminderBatchRecipientReport(BaseModel):
    """Per-recipient report row for a reminder batch."""
    party_code: str
    recipient_name: Optional[str] = None
    phone: Optional[str] = None
    status: str
    queue_status: str
    delivery_status: str
    failure_stage: Optional[str] = None
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    retry_count: int = 0
    is_dead_letter: bool = False
    queue_id: Optional[int] = None
    message_id: Optional[str] = None
    amount_due: Optional[str] = None
    media_attached: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ReminderBatchSummaryReport(BaseModel):
    """Batch-level report summary."""
    batch_id: str
    session_id: Optional[str] = None
    company_id: str = "default"
    template_id: Optional[str] = None
    sent_by: Optional[str] = None
    total_parties: int
    status: str
    queue_success_count: int = 0
    queue_failed_count: int = 0
    skipped_count: int = 0
    delivery_accepted_count: int = 0
    delivery_sent_count: int = 0
    delivery_delivered_count: int = 0
    delivery_read_count: int = 0
    delivery_failed_count: int = 0
    in_flight_count: int = 0
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ReminderBatchReportResponse(BaseModel):
    """Batch report with summary and recipients."""
    batch: Dict[str, Any]
    recipients: List[Dict[str, Any]]
