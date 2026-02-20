# Agent Guidelines for Busy WhatsApp Gateway

## Project Overview

FastAPI-based middleware integrating Busy Accounting Software with WhatsApp providers (Twilio, Meta, Webhook). Runs as a Windows Service with MS Access database connectivity.

**Stack:** Python 3.9+, FastAPI, Pydantic, pyodbc, structlog, pytest

---

## Environment Setup

**Critical:** This is a Windows environment with Git Bash (MinGW).

| Do This | Not This |
|---------|----------|
| `python` | `python3` |
| `./script.bat` | `script.bat` |
| `rm`, `cat` | `del`, `type` |
| `$VAR` | `%VAR%` |
| `"C:\Users\Name\path"` (quoted paths) | Unquoted paths with spaces |

**Available Tools:** Python 3.13, Node.js v25.6.1, NPM 11.4.0, Git 2.53.0, Pip 25.2

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

## Build/Run/Test Commands

```bash
# Development server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Or: ./run-server.bat

# Windows Service
python app/service_wrapper.py install
python app/service_wrapper.py start
# Or: ./manage-service.bat

# Run tests
python tests/test_webhook.py --url http://localhost:8000
# Or: ./run-tests.bat

# Run single test
python -c "from tests.test_webhook import test_health_endpoint; test_health_endpoint()"

# pytest
pytest tests/test_webhook.py::test_health_endpoint -v
pytest --cov=app tests/
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
    APP_NAME: str = "Busy WhatsApp Gateway"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True

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
├── service_wrapper.py   # Windows service wrapper
├── models/
│   ├── __init__.py
│   └── schemas.py       # Pydantic models
├── database/
│   ├── __init__.py
│   └── connection.py    # MS Access/ODBC handler
└── services/
    ├── __init__.py
    ├── whatsapp.py      # WhatsApp providers
    └── busy_handler.py  # Business logic
tests/
└── test_webhook.py      # API test suite
```

---

## Environment Variables

Key variables in `.env`:
- `BDS_FILE_PATH` - Path to Busy .bds database file
- `BDS_PASSWORD` - Database password
- `WHATSAPP_PROVIDER` - Provider: twilio, meta, webhook
- `TWILIO_*` - Twilio credentials
- `META_*` - Meta Business API credentials
- `DEBUG` - Enable debug mode (True/False)
