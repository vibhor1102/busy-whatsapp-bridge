---
trigger: always_on
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
- **[NEW]** `database.companies` - Dictionary mapping sequential IDs (e.g. `database_1`, `database_2`) to `{ bds_file_path, bds_password, company_name }`.
- `X-Company-Id` HTTP header is **required** on backend API requests to route to the correct DB.
- `whatsapp.provider` - Provider: baileys (default)
- `baileys.server_url` - Baileys Node.js server URL (default: http://localhost:3001)
- `baileys.enabled` - Enable Baileys integration (true/false)
- `server.debug` - Enable debug mode (true/false)

## Version Management

- **Source of Truth:** `version.json` (root).
- **Access:** `app/version.py` reads it dynamically. Fallback: `0.0.0.0` (Inno Setup compatible).
- **Builds:** `build-all.bat` reads `version.json` via Python temp-file redirect, passes to Inno Setup via `/DMyAppVersion=X.X.X`.

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