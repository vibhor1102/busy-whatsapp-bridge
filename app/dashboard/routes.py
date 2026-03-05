"""
Dashboard API routes for the web interface.
"""

from fastapi import APIRouter, HTTPException, Header
from datetime import datetime, timedelta
from typing import Optional
import asyncio
import httpx
import structlog

from app.config import get_settings
from app.database.connection import db
from app.database.message_queue import message_db
from app.services.queue_service import queue_service

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


def _validate_company_id(x_company_id: Optional[str]) -> str:
    if not x_company_id:
        raise HTTPException(status_code=400, detail="Missing required header: X-Company-Id")
    settings = get_settings()
    if x_company_id not in settings.database.companies:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown company id '{x_company_id}'. Please select a configured company."
        )
    return x_company_id


@router.get("/stats")
async def get_dashboard_stats(x_company_id: Optional[str] = Header(None)):
    """Get aggregated dashboard statistics."""
    settings = get_settings()
    company_id = _validate_company_id(x_company_id)
    
    # Get queue stats
    queue_stats = queue_service.get_status()
    
    # Get WhatsApp status
    whatsapp_status = await get_whatsapp_provider_status()
    
    # Get message stats using SQL aggregation (efficient)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    
    today_counts = message_db.get_message_counts(start_date=today)
    week_counts = message_db.get_message_counts(start_date=week_ago)
    
    sent_today = today_counts['sent']
    failed_today = today_counts['failed']
    sent_this_week = week_counts['sent']
    
    # Check database connection with retry and explicit error context.
    db_connected, db_error = await asyncio.to_thread(
        db.test_connection_with_error,
        company_id,
        0,      # retries
        0.25,   # delay_seconds (unused when retries=0)
        20.0,   # cache_ttl_success
        10.0,   # cache_ttl_failure
    )
    
    return {
        "system": {
            "version": settings.APP_VERSION,
            "start_time": datetime.now().isoformat(),
            "uptime": 0
        },
        "database_connected": db_connected,
        "database_error": db_error,
        "company_id": company_id,
        "queue": queue_stats,
        "whatsapp": whatsapp_status,
        "messages": {
            "sent_today": sent_today,
            "sent_this_week": sent_this_week,
            "failed_today": failed_today
        }
    }


@router.get("/activity")
async def get_recent_activity(limit: int = 10):
    """Get recent system activity."""
    recent_messages = message_db.get_message_history(limit=limit)
    
    return {
        "messages": recent_messages,
        "count": len(recent_messages)
    }


async def get_whatsapp_provider_status():
    """Get WhatsApp provider status."""
    settings = get_settings()
    
    if settings.WHATSAPP_PROVIDER == "baileys":
        baileys_url = getattr(settings, 'BAILEYS_SERVER_URL', 'http://localhost:3001')
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{baileys_url}/status",
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "state": data.get("data", {}).get("state", "unknown"),
                        "user": data.get("data", {}).get("user", {})
                    }
                else:
                    return {"state": "error", "error": "Baileys returned error"}
        except Exception as e:
            return {"state": "unreachable", "error": str(e)}
    
    return {"state": "configured"}
