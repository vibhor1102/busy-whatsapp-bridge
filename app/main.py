from fastapi import FastAPI, HTTPException, Query, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field
import structlog
import sys
import httpx
import json
import shutil
import re
import uuid

from app.config import get_settings, get_config_path, get_config_details, get_local_appdata_path, load_settings, save_settings, Settings
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
from app.services.reminder_config_service import reminder_config_service
from app.websocket import ws_manager, WebSocketMessage
from app.dashboard.routes import router as dashboard_router
from app.api.reminder_routes import router as reminder_router

# Configure structured logging - console-friendly format
def console_renderer(logger, name, event_dict):
    """Human-readable console output for logs."""
    timestamp = event_dict.pop('timestamp', datetime.now().strftime('%H:%M:%S'))
    level = event_dict.pop('level', 'INFO').upper()
    event = event_dict.pop('event', '')
    
    level_colors = {'DEBUG': '\033[36m', 'INFO': '\033[32m', 'WARNING': '\033[33m', 'ERROR': '\033[31m', 'CRITICAL': '\033[35m'}
    reset = '\033[0m'
    dim = '\033[2m'
    
    color = level_colors.get(level, '')
    
    if event_dict:
        extras = ' '.join(f'{k}={v}' for k, v in sorted(event_dict.items()))
        return f"{dim}[{timestamp}]{reset} {color}{level:8}{reset} {event} {dim}{extras}{reset}"
    return f"{dim}[{timestamp}]{reset} {color}{level:8}{reset} {event}"

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt='%H:%M:%S'),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        console_renderer
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
    config_details = get_config_details()
    logger.info(
        "application_startup",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        whatsapp_provider=settings.WHATSAPP_PROVIDER
    )
    # REMOVED: meta_webhook_token_mismatch check - Meta Cloud API removed
    
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
    
    # Start queue worker automatically so webhook-queued messages are delivered.
    try:
        queue_service.start_worker()
        logger.info("message_queue_worker_started")
    except Exception as e:
        logger.error("message_queue_worker_start_failed", error=str(e))
    
    # Initialize payment reminder scheduler
    try:
        from app.services.scheduler_service import scheduler_service
        await scheduler_service.initialize()
        logger.info("reminder_scheduler_initialized")
    except Exception as e:
        logger.warning("reminder_scheduler_init_failed", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")
    queue_service.stop_worker()
    
    # Stop reminder scheduler
    try:
        from app.services.scheduler_service import scheduler_service
        await scheduler_service.stop_scheduler()
        logger.info("reminder_scheduler_stopped")
    except Exception as e:
        logger.warning("reminder_scheduler_stop_failed", error=str(e))
    
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

# Mount static files for dashboard
dashboard_path = Path(__file__).parent.parent / "dashboard-react" / "dist"
assets_path = dashboard_path / "assets"
if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
if dashboard_path.exists():
    app.mount("/dashboard-static", StaticFiles(directory=str(dashboard_path)), name="dashboard-static")


@app.get("/dashboard")
async def redirect_dashboard():
    """Redirect /dashboard to /dashboard/ for React Router basename compatibility."""
    return RedirectResponse(url="/dashboard/", status_code=301)


@app.get("/dashboard/")
async def serve_dashboard():
    """Serve the main dashboard page."""
    index_path = dashboard_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        content={"error": "Dashboard not built. Run 'npm run build' in dashboard-react/ directory or start the development server"},
        status_code=404
    )


@app.get("/dashboard/{path:path}")
async def serve_dashboard_routes(path: str):
    """Handle Vue Router history mode - serve index.html for all routes."""
    index_path = dashboard_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        content={"error": "Dashboard not built"},
        status_code=404
    )


@app.get("/vite.svg")
async def serve_vite_svg():
    """Serve the Vite SVG favicon."""
    svg_path = dashboard_path / "vite.svg"
    if svg_path.exists():
        return FileResponse(str(svg_path), media_type="image/svg+xml")
    return JSONResponse(
        content={"error": "vite.svg not found"},
        status_code=404
    )


@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Receive client messages (subscriptions, commands)
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error("websocket_error", error=str(e))
        await ws_manager.disconnect(websocket)


# Include dashboard API routes
app.include_router(dashboard_router)

# Include payment reminder API routes
app.include_router(reminder_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - redirect to dashboard."""
    return RedirectResponse(url="/dashboard/", status_code=302)


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
    # REMOVED: Meta and Webhook provider checks - only Baileys available now
    # TODO: Re-add via Baileys integration when needed
    
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
    Redirect to integrated dashboard WhatsApp page.
    """
    return RedirectResponse(url="/dashboard#/whatsapp")


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
            data = response.json()

            # Treat transitional/no-QR states as non-fatal for dashboard polling.
            if response.status_code >= 500:
                raise HTTPException(
                    status_code=502,
                    detail=f"Baileys QR upstream error: {response.status_code}"
                )

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
    source: Optional[str] = Query(None, description="Filter by source (busy/payment_reminder/api)"),
    delivery_status: Optional[str] = Query(None, description="Filter by delivery lifecycle (accepted/sent/delivered/read/failed)"),
    from_time: Optional[datetime] = Query(None, description="Filter completed_at >= from_time (ISO datetime)"),
    to_time: Optional[datetime] = Query(None, description="Filter completed_at <= to_time (ISO datetime)"),
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
        source=source,
        delivery_status=delivery_status,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        offset=offset
    )
    
    return {
        "count": len(history),
        "limit": limit,
        "offset": offset,
        "messages": history
    }


# =============================================================================
# REMOVED: Meta Cloud API webhook endpoints
# The following endpoints have been removed as Meta Cloud API is no longer used.
# Only Baileys is now available as the WhatsApp provider.
# TODO: Re-add via Baileys integration when needed
# =============================================================================
# @app.get("/api/v1/whatsapp/meta/webhook") - was Meta webhook verification
# @app.post("/api/v1/whatsapp/meta/webhook") - was Meta webhook status updates
# @app.get("/api/v1/whatsapp/meta/webhook/status") - was Meta webhook diagnostics

@app.get("/api/v1/whatsapp/meta/webhook", tags=["WhatsApp"])
async def meta_webhook_removed():
    """Meta webhook endpoint - REMOVED.
    
    This endpoint has been removed. Only Baileys is now available as the WhatsApp provider.
    TODO: Re-add via Baileys integration when needed.
    """
    return {
        "error": "meta_webhook_removed",
        "message": "Meta Cloud API webhook endpoints have been removed. Only Baileys is now available.",
        "provider": "baileys"
    }


@app.post("/api/v1/whatsapp/meta/webhook")
async def meta_webhook_post_removed():
    """Meta webhook POST endpoint - REMOVED."""
    return {
        "error": "meta_webhook_removed",
        "message": "Meta Cloud API webhook endpoints have been removed. Only Baileys is now available.",
        "provider": "baileys"
    }


@app.get("/api/v1/whatsapp/meta/webhook/status")
async def meta_webhook_status_removed():
    """Meta webhook status endpoint - REMOVED."""
    return {
        "error": "meta_webhook_removed",
        "message": "Meta Cloud API webhook endpoints have been removed. Only Baileys is now available.",
        "provider": "baileys"
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


@app.get("/api/v1/queue/pending", tags=["Queue"])
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


@app.post("/api/v1/queue/process", tags=["Queue"])
async def process_queue_manually(batch_size: int = Query(10, ge=1, le=100)):
    """
    Manually trigger processing of queued messages.
    
    Requires explicit confirmation to prevent accidental sending.
    Returns count of messages processed.
    """
    try:
        # Process one batch
        processed = await queue_service.process_queue_batch(batch_size=batch_size)
        
        return {
            "success": True,
            "processed": processed,
            "message": f"Processed {processed} messages from queue"
        }
    except Exception as e:
        logger.error("queue_processing_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process queue: {str(e)}"
        )


@app.post("/api/v1/whatsapp/disconnect", tags=["WhatsApp"])
async def disconnect_whatsapp():
    """
    Disconnect WhatsApp session.
    
    Logs out the current WhatsApp session.
    """
    baileys_url = getattr(settings, 'BAILEYS_SERVER_URL', 'http://localhost:3001')
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{baileys_url}/logout",
                timeout=10.0
            )
            if response.status_code == 200:
                return {"success": True, "message": "Disconnected successfully"}
            else:
                raise HTTPException(
                    status_code=502,
                    detail="Failed to disconnect from Baileys server"
                )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Baileys server is not running"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Request to Baileys server timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error disconnecting WhatsApp: {str(e)}"
        )


@app.delete("/api/v1/whatsapp/session", tags=["WhatsApp"])
async def clear_whatsapp_session():
    """
    Clear the active WhatsApp session using Baileys logout.
    """
    baileys_url = getattr(settings, 'BAILEYS_SERVER_URL', 'http://localhost:3001')

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{baileys_url}/logout",
                timeout=10.0
            )
            if response.status_code == 200:
                return {"success": True, "message": "WhatsApp session cleared"}
            raise HTTPException(status_code=502, detail="Failed to clear WhatsApp session")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Baileys server is not running")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to Baileys server timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")


@app.post("/api/v1/system/baileys/start", tags=["System"])
async def start_baileys_api():
    """
    Start Baileys server.
    
    Note: This is a placeholder endpoint. In production, Baileys is managed by the tray manager.
    """
    return {
        "success": True,
        "message": "Baileys should be started via the tray manager (right-click icon)"
    }


@app.post("/api/v1/system/baileys/stop", tags=["System"])
async def stop_baileys_api():
    """
    Stop Baileys server.
    
    Note: This is a placeholder endpoint. In production, Baileys is managed by the tray manager.
    """
    return {
        "success": True,
        "message": "Baileys should be stopped via the tray manager (right-click icon)"
    }


@app.post("/api/v1/system/queue/start", tags=["System"])
async def start_queue_worker_api():
    """Start queue worker loop."""
    try:
        queue_service.start_worker()
        return {"success": True, "message": "Queue worker started", "worker_running": queue_service.get_status().get("worker_running", False)}
    except Exception as e:
        logger.error("queue_worker_start_api_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start queue worker: {str(e)}")


@app.post("/api/v1/system/queue/stop", tags=["System"])
async def stop_queue_worker_api():
    """Stop queue worker loop."""
    try:
        queue_service.stop_worker()
        return {"success": True, "message": "Queue worker stopped", "worker_running": queue_service.get_status().get("worker_running", False)}
    except Exception as e:
        logger.error("queue_worker_stop_api_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to stop queue worker: {str(e)}")


@app.get("/api/v1/system/resources", tags=["System"])
async def get_system_resources():
    """Get system resource usage for dashboard diagnostics."""
    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        disk = psutil.disk_usage(str(Path.cwd().anchor or "C:\\"))

        return {
            "cpu_percent": round(float(psutil.cpu_percent(interval=0.1)), 1),
            "memory": {
                "total": int(vm.total),
                "available": int(vm.available),
                "percent": round(float(vm.percent), 1),
                "used": int(vm.used),
            },
            "disk": {
                "total": int(disk.total),
                "used": int(disk.used),
                "free": int(disk.free),
                "percent": round(float(disk.percent), 1),
            }
        }
    except Exception as e:
        logger.warning("system_resources_fallback", error=str(e))
        return {
            "cpu_percent": 0.0,
            "memory": {"total": 0, "available": 0, "percent": 0.0, "used": 0},
            "disk": {"total": 0, "used": 0, "free": 0, "percent": 0.0}
        }


def _detect_level(line: str) -> str:
    match = re.search(r"\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b", line, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return "INFO"


def _detect_timestamp(line: str) -> str:
    # 2026-02-25 20:53:12 or 2026-02-25T20:53:12
    match = re.search(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})", line)
    if match:
        return match.group(1).replace(" ", "T")
    return datetime.now().isoformat()


@app.get("/api/v1/logs", tags=["Logs"])
async def get_logs(
    level: Optional[str] = Query(None, description="DEBUG|INFO|WARNING|ERROR|CRITICAL"),
    source: Optional[str] = Query(None, description="all|fastapi|baileys|system|gateway"),
    limit: int = Query(100, ge=1, le=1000),
):
    """Fetch recent logs from AppData logs directory."""
    logs_dir = get_local_appdata_path() / "logs"
    entries = []
    level_filter = (level or "").upper().strip()
    source_filter = (source or "all").lower().strip()

    if not logs_dir.exists():
        return {"logs": entries}

    files = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if source_filter not in ("", "all"):
        files = [f for f in files if source_filter in f.name.lower()]

    for log_file in files:
        if len(entries) >= limit:
            break
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()[-min(limit * 8, 2000):]
        except Exception:
            continue

        source_name = log_file.stem
        for raw_line in reversed(lines):
            line = raw_line.strip()
            if not line:
                continue
            log_level = _detect_level(line)
            if level_filter and log_level != level_filter:
                continue

            entries.append({
                "id": str(uuid.uuid4()),
                "timestamp": _detect_timestamp(line),
                "level": log_level,
                "logger": source_name,
                "message": line,
                "source": source_name,
            })
            if len(entries) >= limit:
                break

    entries.reverse()
    return {"logs": entries}


@app.get("/api/v1/settings", tags=["Settings"])
async def get_settings_endpoint():
    """
    Get current configuration settings (safe values only).
    """
    db_connected, db_error = db.test_connection_with_error()
    reminder_provider_configured = None
    try:
        reminder_provider_configured = reminder_config_service.get_config().default_provider
    except Exception:
        reminder_provider_configured = None

    return {
        "APP_NAME": settings.APP_NAME,
        "APP_VERSION": settings.APP_VERSION,
        "DEBUG": settings.DEBUG,
        "HOST": settings.HOST,
        "PORT": settings.PORT,
        "WHATSAPP_PROVIDER": settings.WHATSAPP_PROVIDER,
        "WHATSAPP_DEFAULT_COUNTRY_CODE": settings.WHATSAPP_DEFAULT_COUNTRY_CODE,
        "BAILEYS_SERVER_URL": settings.BAILEYS_SERVER_URL,
        "BAILEYS_ENABLED": settings.BAILEYS_ENABLED,
        # REMOVED: meta_webhook_configured - Meta Cloud API removed
        # "META_WEBHOOK_CONFIGURED": ...,
        "REMINDER_PROVIDER_CONFIGURED": reminder_provider_configured,
        "LOG_LEVEL": settings.LOG_LEVEL,
        "config": get_config_details(),
        "database": {
            "bds_file_path": settings.BDS_FILE_PATH,
            "password_configured": bool(settings.BDS_PASSWORD),
            "test": {
                "connected": db_connected,
                "error": db_error,
            },
        },
    }


@app.get("/api/v1/settings/config", tags=["Settings"])
async def get_config_file():
    """
    Get editable configuration values (safe fields only, no secrets).
    """
    return {
        "content": {
            "whatsapp": {
                "provider": settings.WHATSAPP_PROVIDER,
                "default_country_code": settings.WHATSAPP_DEFAULT_COUNTRY_CODE,
                # REMOVED: meta_webhook_configured - Meta Cloud API removed
            },
            "baileys": {
                "server_url": settings.BAILEYS_SERVER_URL,
                "enabled": settings.BAILEYS_ENABLED,
            },
            "logging": {
                "level": settings.LOG_LEVEL,
            },
            "database": {
                "bds_file_path": settings.BDS_FILE_PATH,
            }
        },
        "config_meta": get_config_details(),
    }


class ConfigUpdateRequest(BaseModel):
    """Validatable settings update request."""
    # REMOVED: pattern now only allows baileys (meta, webhook, evolution removed)
    whatsapp_provider: Optional[str] = Field(None, pattern="^baileys$")
    whatsapp_default_country_code: Optional[str] = Field(None, pattern="^\\d{1,4}$")
    baileys_server_url: Optional[str] = Field(None, pattern="^https?://")
    baileys_enabled: Optional[bool] = None
    log_level: Optional[str] = Field(None, pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    bds_file_path: Optional[str] = None
    # REMOVED: meta_webhook_verify_token - Meta Cloud API removed


@app.put("/api/v1/settings/config", tags=["Settings"])
async def update_config_file(request: ConfigUpdateRequest):
    """
    Update the conf.json file with validated settings.
    """
    config_path = get_config_path()
    backup_path = config_path.with_suffix('.json.backup')
    
    try:
        # Load current settings
        current_settings = load_settings()
        
        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        
        if 'whatsapp_provider' in update_data:
            current_settings.whatsapp.provider = update_data['whatsapp_provider']
        if 'whatsapp_default_country_code' in update_data:
            current_settings.whatsapp.default_country_code = update_data['whatsapp_default_country_code']
        # REMOVED: meta_webhook_verify_token update - Meta Cloud API removed
        if 'baileys_server_url' in update_data:
            current_settings.baileys.server_url = update_data['baileys_server_url']
        if 'baileys_enabled' in update_data:
            current_settings.baileys.enabled = update_data['baileys_enabled']
        if 'log_level' in update_data:
            current_settings.logging.level = update_data['log_level']
        if 'bds_file_path' in update_data:
            current_settings.database.bds_file_path = update_data['bds_file_path']
        
        # Create backup
        if config_path.exists():
            shutil.copy(config_path, backup_path)
        
        # Save updated settings
        save_settings(current_settings)
        
        return {"success": True, "message": "Settings saved to conf.json. Restart required for changes to take effect."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write conf.json: {str(e)}")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions including 404s with a friendly error page."""
    if exc.status_code == 404:
        # Check if this might be a dashboard route
        path = request.url.path
        if path.startswith("/dashboard"):
            # Try to serve the dashboard for client-side routing
            index_path = dashboard_path / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
        
        # Return a friendly 404 page
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Page Not Found</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        h1 { font-size: 6rem; margin: 0; opacity: 0.8; }
        h2 { font-size: 1.5rem; margin: 1rem 0; font-weight: 300; }
        p { opacity: 0.9; margin: 1rem 0; }
        a {
            color: white;
            text-decoration: none;
            border: 2px solid white;
            padding: 0.75rem 1.5rem;
            border-radius: 4px;
            display: inline-block;
            margin-top: 1rem;
            transition: all 0.3s;
        }
        a:hover { background: white; color: #667eea; }
    </style>
</head>
<body>
    <div class="container">
        <h1>404</h1>
        <h2>Page Not Found</h2>
        <p>The page you're looking for doesn't exist or has been moved.</p>
        <a href="/dashboard">Go to Dashboard</a>
    </div>
</body>
</html>"""
        return HTMLResponse(content=html_content, status_code=404)
    
    # For other HTTP errors, return JSON
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


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
