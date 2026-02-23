# Payment Reminder System - Comprehensive Implementation Plan

**Last Updated:** 2026-02-23  
**Status:** Planning Phase - Awaiting Approval  
**Credit Days Discovery:** Found in Master1.I2 (Sales Credit Days)

---

## 1. Executive Summary

A comprehensive payment reminder system that:
- **Automatically calculates** amount due based on sales credit days (Master1.I2)
- **Sends weekly/bi-weekly** WhatsApp reminders with attached ledger PDFs
- **Uses Meta Cloud API only** (not Baileys) for bulk business messaging
- **Provides dual-toggle selection** (temporary/permanent) for flexible batch operations
- **Supports multiple message templates** (5-6 total capacity, 2-3 normal use)
- **Configurable via web dashboard** with APScheduler backend

---

## 2. Credit Days Discovery

### Location
| Table | Column | Purpose |
|-------|--------|---------|
| **Master1** | **I1** | Purchase Credit Days (buying from supplier) |
| **Master1** | **I2** | Sales Credit Days (selling to customer) |

### Usage
- **For Customers (debtors):** Use **I2** (Sales Credit Days)
- **For Suppliers (creditors):** Use **I1** (Purchase Credit Days)
- If value is 0 or null, use **default from config** (30 days)

### Statistics from Production DB
- 8,031 total parties
- 649 parties (8.1%) have Sales Credit defined (I2 > 0)
- 151 parties (1.9%) have Purchase Credit defined (I1 > 0)
- Most common: 30 days (400 parties), 60 days (55 parties)

---

## 3. Amount Due Calculation

### Formula
```
Amount Due = Closing Balance - Recent Sales
Where Recent Sales = Sum of Sales transactions within last [Sales Credit Days]
```

### Logic
1. Fetch party ledger (closing balance, all transactions)
2. Filter Sales vouchers (Type 9) from last N days (N = I2 value or default)
3. Sum those sales amounts
4. Amount Due = Closing Balance - Recent Sales Sum
5. If Amount Due ≤ 0, exclude from reminders (don't show in list)

### Example
```
Party: ABC Textiles
Closing Balance: ₹50,000 Dr (they owe us)
Sales Credit Days: 30 (from Master1.I2)

Sales in last 30 days:
- Invoice #123: ₹15,000
- Invoice #124: ₹10,000
- Total Recent Sales: ₹25,000

Amount Due = ₹50,000 - ₹25,000 = ₹25,000
→ Show in reminder list with ₹25,000 due
```

---

## 4. Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    PAYMENT REMINDER SYSTEM                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌──────────────┐   │
│  │   Scheduler     │     │   Reminder      │     │   Party      │   │
│  │   (APScheduler) │◄────┤   Engine        │────►│   Selector   │   │
│  │                 │     │                 │     │   (Vue.js)   │   │
│  │  ┌───────────┐  │     │  ┌───────────┐  │     │              │   │
│  │  │ Weekly    │  │     │  │ Calculate │  │     │  ┌────────┐  │   │
│  │  │ Bi-weekly │  │     │  │ Amount Due│  │     │  │ Temp   │  │   │
│  │  │ Manual    │  │     │  └───────────┘  │     │  │ Toggle │  │   │
│  │  └───────────┘  │     │                 │     │  └────────┘  │   │
│  └────────┬────────┘     │  ┌───────────┐  │     │  ┌────────┐  │   │
│           │              │  │ Generate  │  │     │  │ Perm   │  │   │
│           │              │  │ Ledger PDF│  │     │  │ Toggle │  │   │
│           ▼              │  └───────────┘  │     │  └────────┘  │   │
│  ┌─────────────────┐     │                 │     └──────────────┘   │
│  │  Config JSON    │     │  ┌───────────┐  │            │           │
│  │  (reminder_     │◄────┤  │  Queue    │  │            ▼           │
│  │   config.json)  │     │  │  Messages │  │     ┌──────────────┐   │
│  └─────────────────┘     │  └─────┬─────┘  │     │  Sortable    │   │
│                          │        │        │     │  List View   │   │
│  ┌─────────────────┐     │        ▼        │     │  (Selected   │   │
│  │  Templates      │     │  ┌───────────┐  │     │   at top)    │   │
│  │  (5-6 stored)   │────►│  │ Meta API  │  │     └──────────────┘   │
│  └─────────────────┘     │  │ (Bulk)    │  │                        │
│                          │  └───────────┘  │                        │
│                          └─────────────────┘                        │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Busy Database                             │    │
│  │  ┌────────┐    ┌────────┐    ┌────────┐    ┌──────────┐    │    │
│  │  │Master1 │    │ Tran1  │    │ Tran2  │    │ Folio1   │    │    │
│  │  │ (I2=   │    │(Headers│    │(Details│    │(Opening  │    │    │
│  │  │Credit) │    │        │    │        │    │ Balance) │    │    │
│  │  └────────┘    └────────┘    └────────┘    └──────────┘    │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 5. Data Models

### 5.1 Pydantic Schemas (`app/models/reminder_schemas.py`)

```python
class PartyReminderInfo(BaseModel):
    """Party information for reminder selection UI"""
    code: str
    name: str
    print_name: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    
    # Financial info
    closing_balance: Decimal
    closing_balance_formatted: str
    amount_due: Decimal
    amount_due_formatted: str
    
    # Credit info (from Master1)
    sales_credit_days: int  # Master1.I2
    purchase_credit_days: Optional[int]  # Master1.I1 (if needed)
    
    # Reminder settings
    permanent_enabled: bool  # Stored in JSON
    temp_enabled: bool       # Session-only for current batch
    
    # Metadata
    last_reminder_sent: Optional[datetime]
    reminder_count: int
    
    # Actions
    can_generate_ledger: bool = True


class AmountDueCalculation(BaseModel):
    """Detailed breakdown of amount due calculation"""
    party_code: str
    party_name: str
    
    closing_balance: Decimal
    credit_days_used: int
    credit_days_source: Literal["master1_i2", "config_default", "override"]
    
    recent_sales_total: Decimal
    recent_sales_count: int
    recent_sales_date_range: Tuple[date, date]
    
    amount_due: Decimal
    calculation_timestamp: datetime


class ReminderConfig(BaseModel):
    """Root configuration stored in reminder_config.json"""
    version: str = "1.0"
    last_updated: datetime
    
    # Global defaults
    default_credit_days: int = 30
    default_provider: str = "meta"
    
    # Scheduling
    schedule: ScheduleConfig
    
    # Party overrides (only stored if different from default)
    parties: Dict[str, PartyConfig]
    
    # Templates
    templates: List[MessageTemplate]
    active_template_id: str = "default"


class PartyConfig(BaseModel):
    """Per-party configuration (stored in JSON if different from default)"""
    enabled: bool = False
    credit_days_override: Optional[int] = None
    custom_template_id: Optional[str] = None
    custom_message: Optional[str] = None
    notes: Optional[str] = None


class ScheduleConfig(BaseModel):
    """Scheduler configuration"""
    enabled: bool = False
    frequency: Literal["weekly", "biweekly"] = "weekly"
    day_of_week: int = 1  # 0=Sunday, 1=Monday, ..., 6=Saturday
    time: str = "10:00"   # 24-hour format
    timezone: str = "Asia/Kolkata"
    batch_size: int = 50  # Messages per batch (Meta API safety)
    delay_between_messages: int = 5  # Seconds between API calls


class MessageTemplate(BaseModel):
    """Message template for reminders"""
    id: str
    name: str
    description: Optional[str]
    content: str
    variables: List[str] = Field(default_factory=lambda: [
        "customer_name", "amount_due", "due_date", 
        "company_name", "credit_days", "ledger_period"
    ])
    is_default: bool = False
    created_at: datetime
    updated_at: datetime


class ReminderBatch(BaseModel):
    """A batch of reminders being sent"""
    batch_id: str
    created_at: datetime
    scheduled_for: Optional[datetime]
    sent_at: Optional[datetime]
    
    template_id: str
    party_count: int
    parties: List[str]  # Party codes
    
    status: Literal["draft", "scheduled", "sending", "completed", "failed", "cancelled"]
    results: Optional[Dict[str, Any]]  # Per-party results


class ReminderHistory(BaseModel):
    """Record of sent reminders"""
    id: str
    party_code: str
    party_name: str
    
    batch_id: str
    sent_at: datetime
    sent_by: Literal["scheduler", "manual"]
    
    template_id: str
    message_content: str
    amount_due: Decimal
    
    status: Literal["queued", "sent", "delivered", "failed"]
    error_message: Optional[str]
    whatsapp_message_id: Optional[str]
```

### 5.2 JSON Config Structure (`data/reminder_config.json`)

```json
{
  "version": "1.0",
  "last_updated": "2026-02-23T18:30:00+05:30",
  
  "default_credit_days": 30,
  "default_provider": "meta",
  
  "schedule": {
    "enabled": true,
    "frequency": "weekly",
    "day_of_week": 1,
    "time": "10:00",
    "timezone": "Asia/Kolkata",
    "batch_size": 50,
    "delay_between_messages": 5
  },
  
  "parties": {
    "1900": {
      "enabled": true,
      "credit_days_override": 45,
      "notes": "VIP customer - extended terms"
    },
    "7160": {
      "enabled": false
    }
  },
  
  "templates": [
    {
      "id": "default",
      "name": "Standard Reminder",
      "description": "Professional and courteous",
      "content": "Dear {customer_name},\n\nThis is a friendly reminder that you have an outstanding balance of ₹{amount_due} with {company_name}.\n\nPlease find your ledger attached for reference.\n\nIf you have any questions, please don't hesitate to contact us.\n\nBest regards,\n{company_name}",
      "variables": ["customer_name", "amount_due", "company_name"],
      "is_default": true,
      "created_at": "2026-02-23T18:30:00+05:30",
      "updated_at": "2026-02-23T18:30:00+05:30"
    },
    {
      "id": "gentle",
      "name": "Gentle Nudge",
      "description": "Soft and friendly tone",
      "content": "Hi {customer_name},\n\nJust a quick reminder about your pending payment of ₹{amount_due}.\n\nYour ledger is attached. Please arrange payment at your earliest convenience.\n\nThanks!\n{company_name}",
      "variables": ["customer_name", "amount_due", "company_name"],
      "is_default": false,
      "created_at": "2026-02-23T18:30:00+05:30",
      "updated_at": "2026-02-23T18:30:00+05:30"
    },
    {
      "id": "urgent",
      "name": "Urgent Notice",
      "description": "For overdue accounts",
      "content": "Dear {customer_name},\n\nURGENT: Your account shows an outstanding balance of ₹{amount_due} which is now overdue.\n\nPlease settle this immediately to avoid further action.\n\nAttached: Account Ledger\n\n{company_name}",
      "variables": ["customer_name", "amount_due", "company_name"],
      "is_default": false,
      "created_at": "2026-02-23T18:30:00+05:30",
      "updated_at": "2026-02-23T18:30:00+05:30"
    }
  ],
  
  "active_template_id": "default"
}
```

---

## 6. Service Architecture

### 6.1 Core Services

```
app/services/
├── reminder_service.py           # Main orchestrator
├── amount_due_calculator.py      # Calculate amount due logic
├── scheduler_service.py          # APScheduler wrapper
├── template_service.py           # Template CRUD and rendering
├── reminder_config_service.py    # JSON config read/write
└── batch_service.py              # Batch processing and tracking
```

### 6.2 Service Details

#### `amount_due_calculator.py`
```python
class AmountDueCalculator:
    """Calculate amount due based on credit days"""
    
    async def calculate_for_party(
        self,
        party_code: str,
        credit_days: Optional[int] = None,
        as_of_date: Optional[date] = None
    ) -> AmountDueCalculation:
        """
        1. Get party info (Master1.I2 for sales credit days)
        2. Get ledger (closing balance)
        3. Get sales transactions in last N days
        4. Sum recent sales
        5. Return AmountDueCalculation
        """
        
    async def calculate_for_all_parties(
        self,
        min_amount_due: Decimal = Decimal("0.01")
    ) -> List[PartyReminderInfo]:
        """Calculate for all parties, filter by min_amount_due"""
```

#### `scheduler_service.py`
```python
class ReminderSchedulerService:
    """APScheduler-based reminder scheduling"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
    async def initialize(self):
        """Load config and schedule jobs"""
        
    async def schedule_reminder_job(self, config: ScheduleConfig):
        """Schedule the recurring reminder job"""
        
    async def trigger_manual_run(self) -> str:
        """Manually trigger reminder run, return batch_id"""
        
    async def pause_scheduler(self):
        """Pause all scheduled jobs"""
        
    async def resume_scheduler(self):
        """Resume scheduled jobs"""
```

#### `reminder_service.py`
```python
class ReminderService:
    """Main service orchestrating reminders"""
    
    async def get_eligible_parties(self) -> List[PartyReminderInfo]:
        """Get all parties with amount_due > 0"""
        
    async def prepare_batch(
        self,
        party_codes: List[str],
        template_id: str,
        schedule_for: Optional[datetime] = None
    ) -> ReminderBatch:
        """Prepare a batch of reminders"""
        
    async def send_batch(
        self,
        batch_id: str,
        send_now: bool = False
    ) -> Dict[str, Any]:
        """Send or queue batch of reminders"""
        
    async def generate_ledger_pdf(self, party_code: str) -> bytes:
        """Generate ledger PDF for attachment"""
```

---

## 7. API Endpoints

### 7.1 Reminder Management

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/v1/reminders/config` | GET | Get full config | Admin |
| `/api/v1/reminders/config` | PUT | Update config | Admin |
| `/api/v1/reminders/parties` | GET | List eligible parties (amount_due > 0) | Admin |
| `/api/v1/reminders/parties/{code}` | GET | Get single party details | Admin |
| `/api/v1/reminders/parties/{code}/ledger` | GET | Generate party ledger PDF | Admin |
| `/api/v1/reminders/parties/{code}` | PUT | Update party config | Admin |
| `/api/v1/reminders/calculate` | POST | Calculate amount due for party(s) | Admin |

### 7.2 Batch Operations

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/v1/reminders/batches` | GET | List all batches | Admin |
| `/api/v1/reminders/batches` | POST | Create new batch | Admin |
| `/api/v1/reminders/batches/{id}` | GET | Get batch details | Admin |
| `/api/v1/reminders/batches/{id}/send` | POST | Send batch immediately | Admin |
| `/api/v1/reminders/batches/{id}/cancel` | POST | Cancel scheduled batch | Admin |

### 7.3 Templates

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/v1/reminders/templates` | GET | List all templates | Admin |
| `/api/v1/reminders/templates` | POST | Create new template | Admin |
| `/api/v1/reminders/templates/{id}` | GET | Get template | Admin |
| `/api/v1/reminders/templates/{id}` | PUT | Update template | Admin |
| `/api/v1/reminders/templates/{id}` | DELETE | Delete template | Admin |
| `/api/v1/reminders/templates/{id}/preview` | POST | Preview with variables | Admin |

### 7.4 Scheduler Control

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/v1/reminders/scheduler/status` | GET | Get scheduler status | Admin |
| `/api/v1/reminders/scheduler/start` | POST | Start scheduler | Admin |
| `/api/v1/reminders/scheduler/stop` | POST | Stop scheduler | Admin |
| `/api/v1/reminders/scheduler/trigger` | POST | Trigger manual run | Admin |

### 7.5 History

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/v1/reminders/history` | GET | Get reminder history (paginated) | Admin |
| `/api/v1/reminders/history/export` | GET | Export history to CSV | Admin |
| `/api/v1/reminders/stats` | GET | Get reminder statistics | Admin |

---

## 8. Frontend UI Design

### 8.1 Main Reminders Page (`/reminders`)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Payment Reminders                                                    [?]   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CONFIGURATION                                                      │   │
│  │                                                                      │   │
│  │  Schedule: [Enabled ■]  Frequency: [Weekly ▼]  Day: [Monday ▼]      │   │
│  │  Time: [10:00 ▼]  Timezone: [Asia/Kolkata ▼]                       │   │
│  │                                                                      │   │
│  │  Default Credit Days: [30]  Batch Size: [50]  Delay: [5s]          │   │
│  │                                                                      │   │
│  │  [Save Config]  [Start Scheduler]  [Trigger Now]                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  MESSAGE TEMPLATE                                                   │   │
│  │                                                                      │   │
│  │  Active Template: [Standard Reminder ▼]              [Edit] [New]  │   │
│  │                                                                      │   │
│  │  Preview:                                                            │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │ Dear {{customer_name}},                                        │ │   │
│  │  │                                                                │ │   │
│  │  │ This is a friendly reminder that you have an outstanding...   │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PARTY SELECTION (42 parties with amount due > ₹0)                  │   │
│  │                                                                      │   │
│  │  [Search by name or code...]  [Sort: Amount Due ▼] [Filter: All ▼]  │   │
│  │                                                                      │   │
│  │  Select: [All] [None]  │  Selected: 15 parties  Total Due: ₹4.2L    │   │
│  │                                                                      │   │
│  │  ═══ SELECTED FOR THIS BATCH ════════════════════════════════════   │   │
│  │                                                                      │   │
│  │  ☑ ANJALI HOME FASHION-PANIPAT      ₹45,230.00   30d   [Ledger]   │   │
│  │    Temp: [On ■]  Permanent: [On ■]  Last: 7 days ago               │   │
│  │                                                                      │   │
│  │  ☑ RAJESH HANDLOOM HOUSE            ₹32,150.00   45d   [Ledger]   │   │
│  │    Temp: [On ■]  Permanent: [Off □]  Last: Never                   │   │
│  │                                                                      │   │
│  │  ☑ PREMIUM TEXTILES                 ₹28,900.00   30d   [Ledger]   │   │
│  │    Temp: [On ■]  Permanent: [On ■]  Credit: [30 ▼]                 │   │
│  │                                                                      │   │
│  │  ═══ NOT SELECTED ═══════════════════════════════════════════════   │   │
│  │                                                                      │   │
│  │  □ VIKAS FABRICS                    ₹18,500.00   30d   [Ledger]   │   │
│  │    Temp: [Off □]  Permanent: [Off □]                               │   │
│  │                                                                      │   │
│  │  □ NORTHERN THREADS                 ₹12,300.00   60d   [Ledger]   │   │
│  │    Temp: [Off □]  Permanent: [On ■]                                │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [Send Now]  [Schedule for Later...]  [Export CSV]  [Refresh]             │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Party Selection Features

**Two-Level Toggle System:**
- **Temporary Toggle:** ☑ / □ - Affects only current batch (stored in browser session)
- **Permanent Toggle:** ☑ / □ - Saves to `reminder_config.json` (default for future)

**Visual Indicators:**
- Selected parties appear at top regardless of sort
- Amount due shown in ₹ format
- Credit days shown (with override dropdown)
- Last reminder sent date
- Ledger button (opens in new tab)

**Sorting Options:**
- Amount Due (High to Low / Low to High)
- Name (A-Z / Z-A)
- Credit Days
- Last Reminder Date
- Party Code

**Filtering:**
- All parties
- Permanent enabled only
- Permanent disabled only
- Never reminded
- Reminded in last 30 days

### 8.3 Template Editor (`/reminders/templates`)

```
┌────────────────────────────────────────────────────────────┐
│ Message Templates                                    [+ New]│
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────────────────────────┐   │
│  │ Templates    │  │ Template: Standard Reminder      │   │
│  │              │  │                                  │   │
│  │ ★ Default    │  │ Name: [Standard Reminder       ] │   │
│  │ • Standard   │  │ Desc: [Professional and...     ] │   │
│  │ • Gentle     │  │                                  │   │
│  │ • Urgent     │  │ Content:                         │   │
│  │ • Final      │  │ ┌────────────────────────────┐   │   │
│  │              │  │ │ Dear {customer_name},      │   │   │
│  │              │  │ │                            │   │   │
│  │              │  │ │ Your balance: ₹{amount_due}│   │   │
│  │              │  │ │ Due date: {due_date}       │   │   │
│  │              │  │ │                            │   │   │
│  │              │  │ │ {company_name}             │   │   │
│  │              │  │ └────────────────────────────┘   │   │
│  │              │  │                                  │   │
│  │              │  │ Available Variables:             │   │
│  │              │  │ {customer_name} {amount_due}    │   │
│  │              │  │ {due_date} {company_name} ...   │   │
│  │              │  │                                  │   │
│  │              │  │ [Save] [Preview] [Set as Default]│   │
│  └──────────────┘  └──────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

### 8.4 Schedule Dialog

```
┌────────────────────────────────────┐
│ Schedule Reminders                 │
├────────────────────────────────────┤
│                                     │
│  Date: [2026-02-28 ▼]              │
│  Time: [14:30 ▼]                   │
│                                     │
│  Selected: 15 parties              │
│  Template: Standard Reminder       │
│  Estimated: 15 WhatsApp messages   │
│                                     │
│  [Confirm Schedule]  [Cancel]      │
└────────────────────────────────────┘
```

---

## 9. Meta API Rate Limiting & Batching

### 9.1 Meta Business API Limits

**Based on Meta documentation:**

| Tier | Daily Limit | Characteristics |
|------|-------------|-----------------|
| Unverified | 250 messages | Business not verified |
| Verified | 1,000 messages | Phone number verified |
| Tier 1 | 10,000 messages | Quality rating high |
| Tier 2 | 100,000 messages | Usage increases |
| Tier 3 | Unlimited | Established business |

**Practical Limits:**
- Recommended: **50 messages per batch** (safe default)
- Configurable: 10-500 range
- Delay between messages: **5 seconds** (300 messages/hour)

### 9.2 Batch Processing Strategy

```python
class BatchProcessor:
    """Process reminders with rate limiting"""
    
    async def process_batch(
        self,
        party_codes: List[str],
        template_id: str,
        batch_size: int = 50,
        delay_seconds: int = 5
    ):
        """
        1. Split into batches of batch_size
        2. Process each batch sequentially
        3. Add delay between messages
        4. Track results
        5. Handle failures with retry
        """
        
    async def send_single_reminder(
        self,
        party_code: str,
        template_id: str
    ) -> ReminderResult:
        """
        1. Calculate amount due
        2. Generate ledger PDF
        3. Compose message with template
        4. Queue to message_queue table
        5. Return result
        """
```

### 9.3 Queue Integration

The reminder system uses the **existing message queue** (`app/database/message_queue.py`):

```
ReminderService → message_queue (SQLite) → queue_service → MetaProvider
```

**Benefits:**
- ✅ Retry logic already implemented
- ✅ Failed messages tracked
- ✅ Non-blocking operation
- ✅ Survives app restarts
- ✅ Existing monitoring dashboard

---

## 10. Implementation Phases

### Phase 1: Foundation (Days 1-2)
- [ ] Create directory structure
- [ ] Implement `reminder_schemas.py` with all Pydantic models
- [ ] Create `reminder_config.json` with default templates
- [ ] Implement `amount_due_calculator.py` with Master1.I2 integration
- [ ] Add credit days query to ledger_data_service
- [ ] Create `.env` configurations

### Phase 2: Core Services (Days 3-4)
- [ ] Implement `reminder_config_service.py` (JSON read/write)
- [ ] Implement `template_service.py` (CRUD + rendering)
- [ ] Implement `scheduler_service.py` (APScheduler)
- [ ] Implement `reminder_service.py` (main orchestrator)
- [ ] Implement `batch_service.py` (batch tracking)

### Phase 3: API Layer (Days 5-6)
- [ ] Create `reminder_routes.py` with all endpoints
- [ ] Add routes to `app/main.py`
- [ ] Implement party listing with filtering/sorting
- [ ] Implement batch creation and sending
- [ ] Implement scheduler control endpoints
- [ ] Add error handling and validation

### Phase 4: Frontend (Days 7-9)
- [ ] Create `Reminders.vue` main page
- [ ] Create `PartySelector.vue` component with dual toggles
- [ ] Create `TemplateEditor.vue` for message templates
- [ ] Create `ScheduleDialog.vue` for scheduling
- [ ] Add API integration in `dashboard/src/services/api.ts`
- [ ] Add reminder routes to Vue Router

### Phase 5: Integration & Testing (Days 10-11)
- [ ] Integrate with existing Meta WhatsApp provider
- [ ] Test PDF generation and attachment
- [ ] Test amount due calculation with real data
- [ ] Test batch sending with rate limiting
- [ ] Test scheduler functionality
- [ ] Performance testing (100-200 parties)
- [ ] End-to-end testing

### Phase 6: Documentation & Polish (Day 12)
- [ ] Write API documentation
- [ ] Create user guide
- [ ] Add inline help tooltips
- [ ] Final UI polish
- [ ] Code review and cleanup

**Total: 12 days** (buffer included)

---

## 11. Environment Configuration

### Add to `.env`:

```env
# ============================================
# Payment Reminder System Configuration
# ============================================

# Enable/disable reminder system
REMINDER_ENABLED=true

# WhatsApp provider for reminders (meta only for bulk)
REMINDER_PROVIDER=meta

# Default credit days when Master1.I2 is 0 or null
REMINDER_DEFAULT_CREDIT_DAYS=30

# Configuration file path
REMINDER_CONFIG_PATH=data/reminder_config.json

# --- Scheduler Settings ---
REMINDER_SCHEDULE_ENABLED=true
REMINDER_SCHEDULE_FREQUENCY=weekly
REMINDER_SCHEDULE_DAY=1  # Monday (0=Sunday)
REMINDER_SCHEDULE_TIME=10:00
REMINDER_SCHEDULE_TIMEZONE=Asia/Kolkata

# --- Rate Limiting ---
REMINDER_BATCH_SIZE=50
REMINDER_DELAY_BETWEEN_MESSAGES=5

# --- Ledger PDF Settings ---
REMINDER_LEDGER_INCLUDE_ALL_TRANSACTIONS=true
REMINDER_LEDGER_DATE_RANGE_DAYS=90
```

---

## 12. File Structure

```
busy-whatsapp-bridge/
│
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── reminder_routes.py        # All reminder endpoints
│   │
│   ├── constants/
│   │   └── reminder_constants.py     # Magic numbers, enums
│   │
│   ├── models/
│   │   └── reminder_schemas.py       # Pydantic models
│   │
│   └── services/
│       ├── reminder_service.py       # Main orchestrator
│       ├── amount_due_calculator.py  # Amount due calculation
│       ├── scheduler_service.py      # APScheduler wrapper
│       ├── template_service.py       # Template management
│       ├── reminder_config_service.py # JSON config handler
│       └── batch_service.py          # Batch processing
│
├── dashboard/
│   └── src/
│       ├── views/
│       │   ├── Reminders.vue         # Main reminder page
│       │   └── ReminderTemplates.vue # Template management
│       │
│       ├── components/
│       │   ├── PartySelector.vue     # Party list with toggles
│       │   ├── PartyListItem.vue     # Single party row
│       │   ├── TemplateEditor.vue    # Template CRUD
│       │   ├── ScheduleDialog.vue    # Schedule modal
│       │   ├── ConfigPanel.vue       # Scheduler config
│       │   └── LedgerPreviewModal.vue # PDF preview
│       │
│       └── services/
│           └── api.ts                # Add reminder API methods
│
├── data/
│   ├── message_queue.db              # Existing
│   └── reminder_config.json          # NEW: Reminder settings
│
└── .env                              # Add reminder configs
```

---

## 13. Key Design Decisions

### 1. Credit Days Source
- **Primary:** Master1.I2 (Sales Credit Days) fetched dynamically
- **Fallback:** Config default (30 days) when I2 = 0
- **Override:** Per-party override stored in JSON config

### 2. Dual Toggle System
- **Temporary:** Session-only, affects current batch only
- **Permanent:** Stored in JSON, becomes default for future
- **Visual:** Selected parties always appear at top, separate sections

### 3. Meta API Only
- **No Baileys:** Designed for bulk business messaging
- **Rate Limiting:** 50 messages/batch, 5-second delays
- **Queue Integration:** Uses existing SQLite queue for reliability

### 4. Ledger PDF
- **Always Attached:** Non-negotiable requirement
- **Generated On-Demand:** When batch is sent
- **Temporary Storage:** Cleaned up after successful send

### 5. Template System
- **5-6 Templates:** Comfortable capacity
- **Variables:** customer_name, amount_due, due_date, company_name, etc.
- **Preview:** Real-time preview with sample data
- **One Active:** Single active template per batch

### 6. Scheduler
- **APScheduler:** AsyncIO-based, runs in FastAPI process
- **Configurable:** Day, time, frequency via web UI
- **Manual Trigger:** Instant run button for ad-hoc reminders
- **Batch Processing:** Large lists split into manageable batches

### 7. Security
- **Local Only:** No network exposure concerns
- **Admin Only:** All reminder endpoints require admin access
- **No PII Storage:** Only party codes stored, data fetched from Busy DB

---

## 14. Success Criteria

✅ **Functional:**
- Calculate amount due correctly using Master1.I2
- Generate and attach ledger PDF to WhatsApp messages
- Send via Meta Cloud API with proper rate limiting
- Support 2-3 message templates (expandable to 5-6)
- Dual-toggle selection (temp/permanent)

✅ **Usability:**
- Intuitive party selection with sorting/filtering
- Clear preview of messages before sending
- Easy template management
- Responsive UI

✅ **Reliability:**
- Graceful handling of missing phone numbers
- Retry logic for failed sends
- Scheduler persists across restarts
- Batch processing doesn't overwhelm Meta API

✅ **Maintainability:**
- Clean separation of concerns
- Comprehensive logging
- Well-documented API
- Type hints throughout

---

## 15. Questions for Final Confirmation

1. **Default Credit Days:** Is 30 days appropriate for parties without Master1.I2 set?

2. **Scheduler:** Should it run as background thread in FastAPI app, or as separate Windows scheduled task?

3. **Due Date Calculation:** Should due date = Today + Credit Days, or based on last transaction date?

4. **Failed Reminders:** Should failed reminders be automatically retried, or require manual retry?

5. **History Retention:** How long to keep reminder history? (suggest 1 year)

6. **Multi-Company:** Will this system work with multiple Busy companies/databases?

**Ready to proceed with implementation?** ✅
