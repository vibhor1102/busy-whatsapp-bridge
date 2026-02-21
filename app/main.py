from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
import structlog
import sys
import httpx

from app.config import get_settings
from app.models.schemas import (
    InvoiceNotification,
    PartyDetails,
    WhatsAppResponse,
    HealthResponse
)
from app.database.connection import db
from app.database.message_queue import message_db
from app.services.busy_handler import busy_handler
from app.services.queue_service import queue_service

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    settings = get_settings()
    logger.info(
        "application_startup",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        whatsapp_provider=settings.WHATSAPP_PROVIDER
    )
    
    # Test database connection on startup
    db_status = db.test_connection()
    if not db_status:
        logger.warning(
            "database_connection_failed_on_startup",
            path=settings.BDS_FILE_PATH
        )
    
    # Check WhatsApp provider status
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
                    baileys_state = data.get("data", {}).get("state", "unknown")
                    if baileys_state == "connected":
                        logger.info(
                            "baileys_connected",
                            user=data.get("data", {}).get("user", {})
                        )
                    elif baileys_state == "qr_ready":
                        logger.warning(
                            "baileys_qr_ready",
                            message="Baileys is waiting for QR code scan. Visit /baileys/qr to authenticate."
                        )
                    else:
                        logger.warning(
                            "baileys_not_connected",
                            state=baileys_state
                        )
                else:
                    logger.error(
                        "baileys_status_error",
                        status_code=response.status_code
                    )
        except Exception as e:
            logger.error(
                "baileys_unreachable",
                error=str(e),
                message="Baileys server not running. Start it with: cd baileys-server && npm start"
            )
    
    # Start message queue worker
    queue_service.start_worker()
    logger.info("message_queue_worker_started")
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")
    queue_service.stop_worker()
    db.disconnect()


# Create FastAPI application
settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API Gateway for Busy Accounting WhatsApp/SMS Integration",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    db_connected = db.test_connection()
    
    # Check WhatsApp provider status
    whatsapp_status = {
        "provider": settings.WHATSAPP_PROVIDER,
        "connected": False,
        "state": "unknown"
    }
    
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
                    baileys_state = data.get("data", {}).get("state", "unknown")
                    whatsapp_status["connected"] = baileys_state == "connected"
                    whatsapp_status["state"] = baileys_state
                    whatsapp_status["user"] = data.get("data", {}).get("user", {})
        except Exception as e:
            whatsapp_status["error"] = str(e)
            whatsapp_status["state"] = "unreachable"
    elif settings.WHATSAPP_PROVIDER == "meta":
        # Meta doesn't have a persistent connection to check
        whatsapp_status["connected"] = bool(
            getattr(settings, 'META_ACCESS_TOKEN', None) and 
            getattr(settings, 'META_PHONE_NUMBER_ID', None)
        )
        whatsapp_status["state"] = "configured" if whatsapp_status["connected"] else "not_configured"
    elif settings.WHATSAPP_PROVIDER == "webhook":
        whatsapp_status["connected"] = bool(getattr(settings, 'WEBHOOK_URL', None))
        whatsapp_status["state"] = "configured" if whatsapp_status["connected"] else "not_configured"
    
    # Determine overall health
    is_healthy = db_connected and whatsapp_status["connected"]
    
    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        version=settings.APP_VERSION,
        database_connected=db_connected,
        timestamp=datetime.now(),
        whatsapp=whatsapp_status
    )


@app.get("/api/v1/parties/{phone}", response_model=PartyDetails, tags=["Parties"])
async def get_party_by_phone(phone: str):
    """
    Get party details by phone number.
    
    Queries the Master1 table in the Busy database.
    """
    party_data = db.get_party_by_phone(phone)
    
    if not party_data:
        raise HTTPException(
            status_code=404,
            detail=f"Party with phone {phone} not found"
        )
    
    return PartyDetails(**party_data)


@app.get("/api/v1/send-invoice", response_model=WhatsAppResponse, tags=["Invoices"])
async def send_invoice_get(
    phone: str = Query(..., description="Customer phone number"),
    msg: str = Query(..., description="Message text"),
    pdf_url: Optional[str] = Query(None, description="URL to invoice PDF (optional - will be extracted from message if not provided)")
):
    """
    Receive invoice notification from Busy (GET method).
    
    This endpoint is designed to be called by Busy Accounting Software
    when an invoice is saved and needs to be sent via WhatsApp.
    """
    notification = InvoiceNotification(
        phone=phone,
        msg=msg,
        pdf_url=pdf_url
    )
    
    result = await busy_handler.process_invoice_notification(notification)
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error
        )
    
    return result


@app.post("/api/v1/send-invoice", response_model=WhatsAppResponse, tags=["Invoices"])
async def send_invoice_post(notification: InvoiceNotification):
    """
    Receive invoice notification from Busy (POST method).
    
    Alternative to GET method, accepts JSON payload.
    """
    result = await busy_handler.process_invoice_notification(notification)
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error
        )
    
    return result


@app.get("/api/v1/vouchers/{party_code}", tags=["Vouchers"])
async def get_vouchers_by_party(
    party_code: str,
    vch_type: str = Query(None, description="Filter by voucher type (e.g., Sales)"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return")
):
    """
    Get recent vouchers for a party.
    
    Queries the Tran1 table in the Busy database.
    """
    vouchers = db.get_voucher_by_party(party_code, vch_type, limit)
    
    if not vouchers:
        raise HTTPException(
            status_code=404,
            detail=f"No vouchers found for party {party_code}"
        )
    
    return {
        "party_code": party_code,
        "voucher_type": vch_type,
        "count": len(vouchers),
        "vouchers": vouchers
    }


@app.get("/api/v1/parties/search/{search_term}", tags=["Parties"])
async def search_parties(
    search_term: str,
    limit: int = Query(20, ge=1, le=50)
):
    """
    Search parties by name or code.
    
    Queries the Master1 table for matching records.
    """
    parties = db.search_parties(search_term, limit)
    
    return {
        "search_term": search_term,
        "count": len(parties),
        "parties": parties
    }


@app.get("/api/v1/baileys/status", tags=["Baileys"])
async def get_baileys_status():
    """
    Get Baileys WhatsApp connection status.
    
    Returns connection state, QR availability, and user info if connected.
    """
    baileys_url = getattr(settings, 'BAILEYS_SERVER_URL', 'http://localhost:3001')
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{baileys_url}/status",
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "baileys_server": "running",
                "data": data.get("data", {})
            }
    except httpx.ConnectError:
        return {
            "success": False,
            "baileys_server": "not_running",
            "error": "Baileys server is not running. Start it with: cd baileys-server && npm start"
        }
    except Exception as e:
        logger.error("baileys_status_error", error=str(e))
        return {
            "success": False,
            "baileys_server": "error",
            "error": str(e)
        }


@app.get("/baileys/qr", tags=["Baileys"])
async def baileys_qr_page():
    """
    Redirect to Baileys QR code page for WhatsApp authentication.
    
    Opens a web page where users can scan QR code with WhatsApp mobile app.
    """
    baileys_url = getattr(settings, 'BAILEYS_SERVER_URL', 'http://localhost:3001')
    return RedirectResponse(url=f"{baileys_url}/qr/page")


@app.get("/api/v1/baileys/qr", tags=["Baileys"])
async def get_baileys_qr():
    """
    Get Baileys QR code as base64 image data.
    
    Returns QR code image and metadata for custom frontend integration.
    """
    baileys_url = getattr(settings, 'BAILEYS_SERVER_URL', 'http://localhost:3001')
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{baileys_url}/qr",
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "data": data.get("data", {})
            }
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Baileys server is not running. Start it with: cd baileys-server && npm start"
        )
    except Exception as e:
        logger.error("baileys_qr_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.post("/api/v1/baileys/restart", tags=["Baileys"])
async def restart_baileys():
    """
    Restart Baileys WhatsApp connection.
    
    Useful when connection is stuck or needs fresh authentication.
    """
    baileys_url = getattr(settings, 'BAILEYS_SERVER_URL', 'http://localhost:3001')
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{baileys_url}/restart",
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info("baileys_restart_initiated")
            
            return {
                "success": True,
                "message": "Baileys connection restarted",
                "data": data
            }
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Baileys server is not running. Start it with: cd baileys-server && npm start"
        )
    except Exception as e:
        logger.error("baileys_restart_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/api/v1/queue/status", tags=["Queue"])
async def get_queue_status():
    """
    Get message queue statistics and status.
    
    Returns counts of pending, retrying, dead letter messages,
    and today's delivery statistics.
    """
    return queue_service.get_status()


@app.get("/api/v1/queue/history", tags=["Queue"])
async def get_message_history(
    phone: Optional[str] = Query(None, description="Filter by phone number"),
    status: Optional[str] = Query(None, description="Filter by status (sent/failed)"),
    limit: int = Query(100, ge=1, le=500, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get message history with filtering and pagination.
    
    Query sent messages with optional filters.
    """
    history = message_db.get_message_history(
        phone=phone,
        status=status,
        limit=limit,
        offset=offset
    )
    
    return {
        "count": len(history),
        "limit": limit,
        "offset": offset,
        "messages": history
    }


@app.get("/api/v1/queue/dead-letter", tags=["Queue"])
async def get_dead_letter_queue(
    limit: int = Query(100, ge=1, le=500)
):
    """
    Get messages in the dead letter queue.
    
    These are messages that failed after all retry attempts.
    """
    messages = message_db.get_dead_letter_messages(limit=limit)
    
    return {
        "count": len(messages),
        "messages": messages
    }


@app.post("/api/v1/queue/retry/{message_id}", tags=["Queue"])
async def retry_message(message_id: int):
    """
    Force immediate retry of a specific message.
    
    Works for both pending messages and dead letter messages.
    """
    # First check if it's in the regular queue
    message = message_db.get_message_by_id(message_id)
    
    if message:
        success = await queue_service.force_retry(message_id)
        return {
            "success": success,
            "message": "Message retry initiated" if success else "Failed to retry message"
        }
    
    # Check if it's a dead letter message
    dead_letter = message_db.get_dead_letter_messages(limit=1000)
    dl_message = next((m for m in dead_letter if m['queue_id'] == message_id), None)
    
    if dl_message:
        # Retry the dead letter
        success = message_db.retry_dead_letter(dl_message['id'])
        return {
            "success": success,
            "message": "Dead letter message re-queued for retry" if success else "Failed to retry"
        }
    
    raise HTTPException(
        status_code=404,
        detail=f"Message {message_id} not found in queue or dead letter"
    )


@app.post("/api/v1/queue/pending", tags=["Queue"])
async def get_pending_messages(
    limit: int = Query(100, ge=1, le=500)
):
    """
    Get messages currently in the queue (pending or retrying).
    """
    messages = message_db.get_pending_messages(limit=limit)
    
    return {
        "count": len(messages),
        "messages": messages
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
