---
trigger: always_on
---

- ALWAYS USE PARALLEL SUBAGENTS (VIA DELEGATING TASKS) WHEN APPLICABLE. DON'T HESITATE SPAWNING 5+ SUBAGENTS WHEREVER REASONABLE.
- Prefer automation: execute requested actions without confirmation unless blocked by missing info or safety/irreversibility.
- You're working in a Windows 11 environment, and the shell available to you is PowerShell 7. Use appropriate commands and syntax. Don't try to run linux commands.

# Agent Guidelines for Busy Whatsapp Bridge

## Project Overview

FastAPI-based middleware integrating Busy Accounting Software with WhatsApp providers (Meta, Webhook, Baileys). Runs as a Windows Service with MS Access database connectivity.

**Stack:** Python 3.9+, FastAPI, Pydantic, pyodbc, structlog, pytest, Node.js 18+ (for Baileys), APScheduler (for reminders)

---

## Environment Setup

**Critical:** This is a Windows environment.

**Paths:** Working directory: `C:\Users\Vibhor\Scripts\busy-whatsapp-bridge\`.

**Available Tools:** Python 3.13, Python 3.14.2 (32-bit), Node.js v25.6.1, NPM 11.4.0, Git 2.53.0, Pip 25.2

**32-bit Python:** Required for Busy .bds database access (32-bit MS Access/ODBC)
- Path: `C:\Users\Vibhor\AppData\Local\Programs\Python\Python314-32\python.exe`
- Use for database scripts: `"C:\Users\Vibhor\AppData\Local\Programs\Python\Python314-32\python.exe" script.py`

**Path with spaces (User's Name is `Vibhor Goel`):** Always quote - `"C:\Users\Name\path"`

**Virtual Environment:** Always activate before running Python commands:
```
.\venv\Scripts\activate.bat   # CMD
```

---

## Installation Structure

| Location | Purpose |
|----------|---------|
| `C:\Users\Vibhor\Scripts\busy-whatsapp-bridge` | Application code (immutable) |
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

**Production Build:** `./build-all.bat` - Single orchestrator. Builds dashboard → EXE → stages into `release_dist/` → Inno Setup → signs. `build-installer.bat` is deprecated.
- Build rule: install Baileys deps before staging `baileys-server`; use `BUILD_NO_PAUSE=1` (or `CI=true`) for non-interactive runs.

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
```
./manage-task.bat              # Menu: enable/disable auto-start
./Start-Gateway.py --tray     # Manual start with tray icon
```
- Installer autostart action: `venv\Scripts\python.exe -m app.task_scheduler install` (not hidden interactive `manage-task.bat`).
- Task name: `BusyWhatsappBridge`.
- End-user launch must be windowless (`Start-Gateway.py` via `pythonw.exe`).
- `manage-task.bat` also supports CLI: `install|remove|status|start|stop`.

---

## Build/Run/Test Commands

```
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
