from fastapi import FastAPI, HTTPException, Query, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field
import structlog
import sys
import httpx
import json
import shutil

from app.config import get_settings, get_config_path, load_settings, save_settings, Settings
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
dashboard_path = Path(__file__).parent.parent / "dashboard" / "dist"
assets_path = dashboard_path / "assets"
if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
if dashboard_path.exists():
    app.mount("/dashboard-static", StaticFiles(directory=str(dashboard_path)), name="dashboard-static")


@app.get("/dashboard")
async def serve_dashboard():
    """Serve the main dashboard page."""
    index_path = dashboard_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        content={"error": "Dashboard not built. Run 'npm run build' in dashboard/ directory"},
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


@app.get("/api/v1/settings", tags=["Settings"])
async def get_settings_endpoint():
    """
    Get current configuration settings (safe values only).
    """
    return {
        "APP_NAME": settings.APP_NAME,
        "APP_VERSION": settings.APP_VERSION,
        "DEBUG": settings.DEBUG,
        "HOST": settings.HOST,
        "PORT": settings.PORT,
        "WHATSAPP_PROVIDER": settings.WHATSAPP_PROVIDER,
        "BAILEYS_SERVER_URL": settings.BAILEYS_SERVER_URL,
        "BAILEYS_ENABLED": settings.BAILEYS_ENABLED,
        "LOG_LEVEL": settings.LOG_LEVEL,
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
        }
    }


class ConfigUpdateRequest(BaseModel):
    """Validatable settings update request."""
    whatsapp_provider: Optional[str] = Field(None, pattern="^(baileys|meta|webhook|evolution)$")
    baileys_server_url: Optional[str] = Field(None, pattern="^https?://")
    baileys_enabled: Optional[bool] = None
    log_level: Optional[str] = Field(None, pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    bds_file_path: Optional[str] = None


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
