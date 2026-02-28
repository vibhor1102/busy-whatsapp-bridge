- ALWAYS USE PARALLEL SUBAGENTS (VIA DELEGATING TASKS) WHEN APPLICABLE. DON'T HESITATE SPAWNING 5+ SUBAGENTS WHEREVER REASONABLE.
- Prefer automation: execute requested actions without confirmation unless blocked by missing info or safety/irreversibility.

# Agent Guidelines for Busy Whatsapp Bridge

## Project Overview

FastAPI-based middleware integrating Busy Accounting Software with WhatsApp providers (Meta, Webhook, Baileys). Runs as a Windows Service with MS Access database connectivity.

**Stack:** Python 3.9+, FastAPI, Pydantic, pyodbc, structlog, pytest, Node.js 18+ (for Baileys), APScheduler (for reminders)

---

## Environment Setup

**Critical:** This is a Windows environment with Git Bash (MinGW).

**Paths:** Working directory: `C:\Program Files\BusyWhatsappBridge\`. Config: `%APPDATA%\BusyWhatsappBridge\`. Source junction: `C:\Users\Vibhor\Scripts\busy-whatsapp-bridge\` (knowledge only, never use).

| Do This | Not This |
|---------|----------|
| `python` | `python3` |
| `./script.bat` | `script.bat` |
| `rm`, `cat` | `del`, `type` |
| `$VAR` | `%VAR%` |
| `"C:\Users\Name\path"` (quoted paths) | Unquoted paths with spaces |

**Available Tools:** Python 3.13, Python 3.14.2 (32-bit), Node.js v25.6.1, NPM 11.4.0, Git 2.53.0, Pip 25.2

**32-bit Python:** Required for Busy .bds database access (32-bit MS Access/ODBC)
- Path: `C:\Users\Vibhor\AppData\Local\Programs\Python\Python314-32\python.exe`
- Use for database scripts: `"C:\Users\Vibhor\AppData\Local\Programs\Python\Python314-32\python.exe" script.py`

**Working Commands:** All standard Unix commands (ls, cat, rm, cp, mv, grep, find, head, tail, chmod, etc.)

**NOT Available:** `man`, `python3`

**Path with spaces (User's Name is `Vibhor Goel`):** Always quote - `"C:\Users\Name\path"`

**Virtual Environment:** Always activate before running Python commands:
```bash
source venv/Scripts/activate  # Git Bash
# OR
.\venv\Scripts\activate.bat   # CMD
```

---

## Installation Structure

| Location | Purpose |
|----------|---------|
| `C:\Program Files\BusyWhatsappBridge\` | Application code (immutable) |
| `%APPDATA%\BusyWhatsappBridge\` | Configuration & mutable data |

**AppData Structure:**
```
%APPDATA%\BusyWhatsappBridge\
├── conf.json              # Main configuration
├── data\
│   ├── messages.db        # Message queue SQLite database
│   └── reminder_config.json  # Payment reminder settings
├── auth\
│   └── baileys_session\   # WhatsApp Web session credentials
└── logs\                  # Application logs
    ├── gateway_YYYYMMDD.log
    └── service.log
```

---

## Build System Guide

Reference: `docs/BUILD_SYSTEM_GUIDE.md` - Complete Windows application build instructions.

**Dashboard:** React 19 + TypeScript in `dashboard-react/` (not `dashboard/`)

**One-File Philosophy:**
- `run-dev.bat` - Development launcher (one file, auto-builds dashboard)
- `run.py` - Production launcher (one file, system tray, process orchestration)

**Production Build:** `./build-all.bat` - Builds dashboard → EXE → installer

---

## Bundled Distribution (No Python Required!)

This is a **portable bundled distribution** with Python and all dependencies included.

**Bundled Components:**
- `python/` - Embeddable Python 3.13 (32-bit)
- `venv/` - Virtual environment with all dependencies pre-installed
- `baileys-server/` - Node.js WhatsApp bridge

**Management Scripts:**
- `setup-bundled.bat` - First-time setup (creates venv, configures)
- `manage-task.bat` - Task Scheduler menu (enable/disable auto-start)
- `build-release.bat` - Creates distribution package
- `Start-Gateway.py` - Main launcher (uses bundled Python)

**Auto-Start via Task Scheduler:**
```bash
./manage-task.bat              # Menu: enable/disable auto-start
./Start-Gateway.py --tray     # Manual start with tray icon
```

---

## Build/Run/Test Commands

```bash
# Run tests
./venv/Scripts/pytest tests/ -v
./venv/Scripts/python tests/test_webhook.py
./venv/Scripts/python tests/test_queue.py

# Development server
./venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Task Scheduler management
./venv/Scripts/python -m app.task_scheduler install    # Enable auto-start
./venv/Scripts/python -m app.task_scheduler status     # Check status
./manage-task.bat                                      # Interactive menu
```

**Key Files:**
- `app/task_scheduler.py` - Task Scheduler Python wrapper
- `manage-task.bat` - Interactive task management menu
- `setup-bundled.bat` - First-time setup script
- `build-release.bat` - Creates distribution package
```

---

## Code Style Guidelines

### Imports Ordering
```python
# 1. Standard library
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any

# 2. Third-party
import httpx
import pyodbc
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# 3. Local
from app.config import get_settings
from app.models.schemas import WhatsAppMessage
```

### Type Hints & Naming
- **Required:** All function parameters and return types
- Use `Optional[T]` for nullable values
- **Classes:** PascalCase (`WhatsAppProvider`)
- **Functions:** snake_case (`send_message`)
- **Constants:** UPPER_SNAKE_CASE in Settings
- **Private:** Leading underscore (`_connection`)

```python
def get_party_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
    ...
```

### Error Handling
Use structured logging with `structlog` and snake_case keys:

```python
logger = structlog.get_logger()

try:
    result = await operation()
except httpx.HTTPError as e:
    logger.error("operation_http_error", error=str(e))
    return Response(success=False, error=f"HTTP Error: {str(e)}")
except Exception as e:
    logger.error("operation_failed", error=str(e), exc_info=True)
    raise HTTPException(status_code=500, detail=str(e))
```

### Pydantic Schemas
```python
class InvoiceNotification(BaseModel):
    phone: str = Field(..., description="Customer phone number")
    msg: str = Field(..., description="Message text")
    pdf_url: Optional[str] = Field(None, description="URL to invoice PDF")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+919876543210",
                "msg": "Your invoice is ready",
                "pdf_url": "https://example.com/inv.pdf"
            }
        }
```

### Configuration
```python
class Settings(BaseSettings):
    server: ServerSettings
    database: DatabaseSettings
    
    class Config:
        pass

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### Database Access
```python
@contextmanager
def get_cursor(self):
    conn = None
    try:
        conn = self.connect()
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("database_error", error=str(e))
        raise
    finally:
        if conn:
            conn.close()
```

### Async Patterns
```python
async def send_message(self, message: WhatsAppMessage) -> WhatsAppResponse:
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
```

---

## Project Structure

```
app/
├── __init__.py
├── main.py              # FastAPI app, routes
├── config.py            # Settings configuration
├── task_scheduler.py    # Windows Task Scheduler integration
├── models/
│   ├── __init__.py
│   └── schemas.py       # Pydantic models
├── database/
│   ├── __init__.py
│   ├── connection.py    # MS Access/ODBC handler
│   └── message_queue.py # SQLite queue/history database
└── services/
    ├── __init__.py
    ├── whatsapp.py      # WhatsApp providers
    ├── busy_handler.py  # Business logic
    └── queue_service.py # Message queue processing
```

---

## Configuration

Configuration stored in `%APPDATA%\BusyWhatsappBridge\conf.json`:
- `database.bds_file_path` - Path to Busy .bds database file
- `database.bds_password` - Database password
- `whatsapp.provider` - Provider: baileys (default), meta, webhook, evolution
- `whatsapp.meta_*` - Meta Business API credentials
- `baileys.server_url` - Baileys Node.js server URL (default: http://localhost:3001)
- `baileys.enabled` - Enable Baileys integration (true/false)
- `server.debug` - Enable debug mode (true/false)

## Baileys (WhatsApp Web)

Node.js bridge service (`baileys-server/`) provides WhatsApp Web integration via Baileys library.

**Architecture:** Python FastAPI → HTTP → Node.js Express → Baileys → WhatsApp Web

**Session Storage:** `baileys-server/auth/baileys_session/` (portable, persistent)

**QR Flow:** Server generates QR → SSE pushes to browser → User scans with WhatsApp mobile → Session saved → Auto-reconnect on restart

**Endpoints:**
- `/qr/page` - Web UI with live QR (SSE real-time updates)
- `/qr/stream` - Server-Sent Events for instant QR updates
- `/status` - Connection status
- `/send` - Send text message
- `/send-media` - Send document/PDF

## Busy Integration

**Webhook URL:** `http://<server>:8000/api/v1/send-invoice?phone={MobileNo}&msg={Message}`

**PDF Handling:** System extracts PDF URLs from message text automatically (pattern: `files.busy.in/?[code]`). The `pdf_url` parameter is optional.

**Busy SMS Template:** Use short templates. Busy sends data as multiple GET requests (originally 33 chunks for full invoice). Short SMS template = concise message with embedded PDF URL.

**Database:** Optional. Webhook works without DB connection (health shows "degraded" but functional). Requires 32-bit Python.

**Database file:** `C:\Users\Vibhor\Desktop\COMP0012\db12025.bds`

**Key Files:**
- `app/services/busy_handler.py` - Processes Busy webhooks, extracts PDF from message
- `app/main.py` - Endpoint: `GET /api/v1/send-invoice`

## Message Queue System (New)

**Purpose:** Reliable message delivery with retry logic and history tracking.

**Features:**
- SQLite-based queue (`data/messages.db`)
- Automatic retry with exponential backoff: immediate → 30s → 5min → 15min → 1hr
- Dead letter queue for permanently failed messages (after 5 retries)
- Message history with filtering by phone, status, date
- Background worker processes messages automatically
- Non-blocking: Busy webhook returns immediately, messages queued for delivery

**API Endpoints:**
- `GET /api/v1/queue/status` - Queue statistics
- `GET /api/v1/queue/pending` - Pending/retrying messages
- `GET /api/v1/queue/history` - Sent/failed message history
- `GET /api/v1/queue/dead-letter` - Failed messages (5+ retries)
- `POST /api/v1/queue/retry/{id}` - Force retry a message

**Database Tables:**
- `message_queue` - Active messages (pending/retrying)
- `message_history` - Completed messages (sent/failed)
- `dead_letter_queue` - Permanently failed messages

**Key Files:**
- `app/database/message_queue.py` - Queue database operations
- `app/services/queue_service.py` - Queue worker and processing logic
- `app/services/busy_handler.py` - Now queues messages instead of direct send

## Payment Reminder System

**Purpose:** Automated weekly/bi-weekly payment reminders with ledger PDFs sent via Meta WhatsApp API.

**Key Features:**
- Calculates amount due: Closing Balance - Recent Sales (within credit days from Master1.I2)
- Dual-toggle selection: Temporary (current batch) + Permanent (stored in JSON)
- 5 Meta-compliant message templates
- APScheduler for weekly/bi-weekly automated sending
- Batch processing with rate limiting (50 msg/batch, 5s delay)
- Full dashboard UI at `/dashboard/#/reminders`

**Architecture:**
- `app/api/reminder_routes.py` - 25+ API endpoints
- `app/services/reminder_service.py` - Main orchestrator
- `app/services/amount_due_calculator.py` - Amount due calculation using Master1.I2
- `app/services/scheduler_service.py` - APScheduler wrapper
- `app/services/template_service.py` - Template rendering
- `app/services/reminder_config_service.py` - JSON config persistence
- `data/reminder_config.json` - All settings, templates, party configs
- `dashboard/src/views/Reminders.vue` - Main UI
- `dashboard/src/components/TemplateEditor.vue` - Template management

**Amount Due Formula:** `Closing Balance - Sum of Sales vouchers in last N days` (N = Master1.I2 or default 30)

**Config Structure (`reminder_config.json`):**
```json
{
  "version": "1.0",
  "currency_symbol": "₹",
  "company": {
    "name": "Your Company Name",
    "contact_phone": "7206366664",
    "address": null
  },
  "schedule": {
    "enabled": false,
    "frequency": "weekly",
    "day_of_week": 1,
    "time": "10:00",
    "timezone": "Asia/Kolkata",
    "batch_size": 50,
    "delay_between_messages": 5
  },
  "ledger": {
    "date_range_days": 90,
    "include_all_transactions": true
  },
  "history": {
    "retention_days": 365
  },
  "limits": {
    "max_templates": 6,
    "max_batch_size": 500,
    "max_delay_between_messages": 60
  },
  "templates": [...],
  "active_template_id": "standard",
  "parties": {}
}
```

**Template Variables:** `{customer_name}`, `{company_name}`, `{amount_due}`, `{currency_symbol}`, `{credit_days}`, `{contact_phone}`, `{party_code}`, `{phone}`

**API Endpoints:**
- `GET/PUT /api/v1/reminders/config` - Full configuration
- `GET/PUT /api/v1/reminders/config/company` - Company settings
- `GET/PUT /api/v1/reminders/config/currency` - Currency symbol
- `GET/PUT /api/v1/reminders/config/schedule` - Scheduler settings
- `GET /api/v1/reminders/parties` - List eligible parties
- `POST /api/v1/reminders/batch` - Create/send batch
- `GET /api/v1/reminders/templates` - List templates
- `POST /api/v1/reminders/templates` - Create template
- `PUT/DELETE /api/v1/reminders/templates/{id}` - Update/delete template
- `POST /api/v1/reminders/templates/{id}/active` - Set active template
- `GET/POST /api/v1/reminders/scheduler/status` - Scheduler control

**Env Variables:**
- `REMINDER_ENABLED` - Enable system
- `REMINDER_PROVIDER` - Only "meta" for bulk
- `REMINDER_DEFAULT_CREDIT_DAYS` - Fallback when Master1.I2 = 0
- `REMINDER_SCHEDULE_*` - Scheduler config
- `BAILEYS_AUTH_DIR` - Path to Baileys session data (auto-set by run.py)

---

## AppData Structure

All user data is stored in `%APPDATA%\BusyWhatsappBridge\`:
- `conf.json` - Main configuration
- `data/` - Message queue and reminder config
- `auth/` - Baileys session credentials
- `logs/` - Application logs

**Key Files:**
- `app/config.py:get_appdata_path()` - Returns AppData base directory
- All database/config services use AppData paths exclusively
