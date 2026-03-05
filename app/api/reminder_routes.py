"""
Payment Reminder API Routes

Provides endpoints for:
- Reminder configuration management
- Party selection and management
- Batch operations
- Template management
- Scheduler control
- Statistics and history
"""
import asyncio
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, Header
from pydantic import BaseModel, Field

import structlog

from app.models.reminder_schemas import (
    PartyReminderInfo,
    PaginatedPartyReminderResponse,
    ReminderSnapshotStatus,
    RefreshStats,
    ReminderConfig,
    ScheduleConfig,
    MessageTemplate,
    PartyConfig,
    ReminderStats,
    AmountDueCalculation,
    CreateBatchRequest,
    UpdatePartyRequest,
    PreviewTemplateRequest,
)
from app.services.reminder_service import reminder_service
from app.services.reminder_config_service import reminder_config_service
from app.services.template_service import template_service
from app.services.amount_due_calculator import amount_due_calculator
from app.services.anti_spam_service import anti_spam_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/reminders", tags=["Payment Reminders"])


def get_company_id(x_company_id: str = Header("default")) -> str:
    """Dependency to extract company ID from headers."""
    return x_company_id

# ============================================
# Configuration Endpoints
# ============================================

@router.get("/config", response_model=ReminderConfig)
async def get_reminder_config(company_id: str = Depends(get_company_id)):
    """Get full reminder configuration"""
    try:
        config = reminder_config_service.get_config(scope_key=company_id)
        return config
    except Exception as e:
        logger.error("get_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_reminder_config(config: ReminderConfig, company_id: str = Depends(get_company_id)):
    """Update reminder configuration"""
    try:
        reminder_config_service.save_config(config, scope_key=company_id)
        logger.info("config_updated")
        return {"status": "success", "message": "Configuration updated"}
    except Exception as e:
        logger.error("update_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))



# ============================================
# Party Management Endpoints
# ============================================

@router.get("/parties", response_model=PaginatedPartyReminderResponse)
async def list_eligible_parties(
    search: Optional[str] = Query(None, description="Search by name or code"),
    sort_by: str = Query("amount_due", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    filter_by: str = Query("all", description="Filter option"),
    min_amount: Optional[Decimal] = Query(None, description="Minimum amount due"),
    include_zero: bool = Query(False, description="Include zero/negative due rows"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=5000, description="Page size"),
    company_id: str = Depends(get_company_id),
):
    """Get debtor parties for reminders, with optional minimum amount filter."""
    try:
        # Default hides non-positive dues unless include_zero=true.
        if min_amount is not None:
            min_amt = min_amount
        elif include_zero:
            min_amt = None
        else:
            min_amt = Decimal("0.01")

        page = reminder_service.get_eligible_parties_page(
            min_amount_due=min_amt,
            search=search,
            filter_by=filter_by,
            include_zero=include_zero,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit,
            company_id=company_id,
        )
        return PaginatedPartyReminderResponse(**page)
        
    except Exception as e:
        logger.error("list_parties_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot/status", response_model=ReminderSnapshotStatus)
async def get_snapshot_status(company_id: str = Depends(get_company_id)):
    """Return current reminder snapshot freshness and row counts."""
    try:
        return ReminderSnapshotStatus(**reminder_service.get_snapshot_status(company_id=company_id))
    except Exception as e:
        logger.error("get_snapshot_status_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/refresh", response_model=ReminderSnapshotStatus)
async def refresh_snapshot(company_id: str = Depends(get_company_id)):
    """Recompute exact amount-due snapshot for all debtor parties."""
    try:
        # Run blocking ODBC queries in a thread pool to avoid starving the event loop
        status = await asyncio.to_thread(
            reminder_service.refresh_snapshot, company_id=company_id
        )
        return ReminderSnapshotStatus(**status)
    except Exception as e:
        logger.error("refresh_snapshot_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/refresh-stats", response_model=RefreshStats)
async def get_refresh_stats(company_id: str = Depends(get_company_id)):
    """Get refresh statistics for progress tracking and staleness checks."""
    try:
        stats = reminder_config_service.get_refresh_stats(scope_key=company_id)
        return RefreshStats(**stats)
    except Exception as e:
        logger.error("get_refresh_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parties/{party_code}", response_model=PartyReminderInfo)
async def get_party_details(party_code: str, company_id: str = Depends(get_company_id)):
    """Get detailed information for a specific party"""
    try:
        return await reminder_service.get_party_info(party_code, company_id=company_id)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_party_error", party_code=party_code, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parties/{party_code}/ledger")
async def get_party_ledger_pdf(party_code: str, company_id: str = Depends(get_company_id)):
    """Generate and download ledger PDF for a party"""
    try:
        pdf_bytes = await reminder_service.generate_ledger_pdf(party_code, company_id=company_id)
        
        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ledger_{party_code}.pdf"
            }
        )
        
    except Exception as e:
        logger.error("generate_ledger_error", party_code=party_code, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/parties/{party_code}")
async def update_party_config(
    party_code: str, request: UpdatePartyRequest, company_id: str = Depends(get_company_id)
):
    """Update party configuration (permanent settings)"""
    try:
        party = await reminder_service.update_party_selection(
            party_code=party_code,
            permanent_enabled=request.permanent_enabled,
            credit_days_override=request.credit_days_override,
            custom_template_id=request.custom_template_id,
            notes=request.notes,
            company_id=company_id,
        )

        return {
            "status": "success",
            "party": party,
            "message": "Party configuration updated"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("update_party_error", party_code=party_code, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parties/{party_code}/calculate", response_model=AmountDueCalculation)
async def calculate_amount_due(
    party_code: str,
    credit_days_override: Optional[int] = None,
    company_id: str = Depends(get_company_id)
):
    """Calculate amount due for a specific party with optional credit days override"""
    try:
        calculation = await amount_due_calculator.calculate_for_party(
            party_code=party_code,
            credit_days=credit_days_override,
            company_id=company_id
        )
        return calculation
        
    except Exception as e:
        logger.error("calculate_amount_due_error", party_code=party_code, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Batch Operations Endpoints
# ============================================

@router.post("/batch")
async def send_reminders_batch(
    request: CreateBatchRequest, 
    background_tasks: BackgroundTasks,
    company_id: str = Depends(get_company_id)
):
    """Send reminders to selected parties immediately (via background task)"""
    try:
        from datetime import timedelta

        # --- Validation 1: Data freshness (must be < 2 hours old) ---
        refresh_stats = reminder_config_service.get_refresh_stats(scope_key=company_id)
        last_refresh = refresh_stats.get("last_refresh_at")
        if last_refresh:
            last_refresh_dt = datetime.fromisoformat(last_refresh)
            staleness = datetime.now() - last_refresh_dt
            if staleness > timedelta(hours=2):
                hours_ago = round(staleness.total_seconds() / 3600, 1)
                logger.warning("stale_data_blocking_send", company_id=company_id, hours_ago=hours_ago)
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "stale_data",
                        "message": f"Data was last refreshed {hours_ago} hours ago. Please refresh before sending.",
                        "last_refreshed_at": last_refresh,
                    }
                )
        else:
            logger.warning("no_snapshot_blocking_send", company_id=company_id)
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "stale_data",
                    "message": "Data has never been refreshed. Please refresh before sending.",
                    "last_refreshed_at": None,
                }
            )

        # --- Validation 2: Reminder cooldown ---
        antispam_config = anti_spam_service.get_config()
        cooldown_enabled = antispam_config.enabled and antispam_config.reminder_cooldown_enabled
        
        logger.info(
            "checking_cooldown", 
            company_id=company_id, 
            cooldown_enabled=cooldown_enabled,
            global_enabled=antispam_config.enabled,
            per_feature_enabled=antispam_config.reminder_cooldown_enabled
        )

        if cooldown_enabled:
            last_sent = refresh_stats.get("last_reminder_sent_at")
            if last_sent:
                last_sent_dt = datetime.fromisoformat(last_sent)
                cooldown_minutes = antispam_config.reminder_cooldown_minutes
                cooldown_delta = timedelta(minutes=cooldown_minutes)
                time_since = datetime.now() - last_sent_dt
                
                if time_since < cooldown_delta:
                    remaining = cooldown_delta - time_since
                    remaining_min = int(remaining.total_seconds() / 60)
                    logger.warning("cooldown_active_blocking_send", company_id=company_id, remaining_min=remaining_min)
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "cooldown_active",
                            "message": f"Reminders were sent {int(time_since.total_seconds() / 60)} minutes ago. Please wait {remaining_min} more minutes.",
                            "last_sent_at": last_sent,
                            "cooldown_minutes": cooldown_minutes,
                            "remaining_minutes": remaining_min,
                        }
                    )

        # Pre-create identifiers and session so we can return them immediately
        batch_id = str(uuid.uuid4())
        session = await anti_spam_service.create_session(
            party_codes=request.party_codes,
            template_id=request.template_id
        )

        # Persist user intent at send-start success (validated + session created).
        reminder_service.persist_selection_preferences_on_send_start(
            selected_party_codes=request.party_codes,
            company_id=company_id,
        )
        reminder_service.persist_explicit_template_overrides(
            explicit_overrides=getattr(request, "party_templates", None),
            company_id=company_id,
        )

        # Define the background task wrapper
        async def _background_send():
            try:
                logger.info("background_batch_started", batch_id=batch_id, session_id=session.session_id)
                await reminder_service.send_reminders_to_parties(
                    party_codes=request.party_codes,
                    template_id=request.template_id,
                    sent_by="manual",
                    party_templates=getattr(request, 'party_templates', None),
                    company_id=company_id,
                    batch_id=batch_id,
                    session=session
                )
                
                # Record that reminders were sent for this company
                try:
                    reminder_config_service.record_reminder_sent(scope_key=company_id)
                    logger.info("reminder_sent_recorded", batch_id=batch_id)
                except Exception as rec_err:
                    logger.warning("failed_to_record_reminder_sent", error=str(rec_err))
                    
                logger.info("background_batch_completed", batch_id=batch_id)
            except Exception as e:
                logger.error("background_batch_failed", batch_id=batch_id, error=str(e), exc_info=True)

        # Schedule the background task
        background_tasks.add_task(_background_send)

        return {
            "status": "success",
            "batch_id": batch_id,
            "session_id": session.session_id,
            "message": f"Reminder batch initiated for {len(request.party_codes)} parties. Processing in background."
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("send_reminders_batch_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule")
async def schedule_reminders(request: CreateBatchRequest, company_id: str = Depends(get_company_id)):
    """Schedule reminders for later delivery"""
    try:
        if not request.schedule_for:
            raise HTTPException(status_code=400, detail="schedule_for is required for scheduled reminders")

        schedule_for = request.schedule_for
        if schedule_for <= datetime.now(schedule_for.tzinfo):
            raise HTTPException(status_code=400, detail="schedule_for must be a future datetime")

        batch_id = f"scheduled-{schedule_for.strftime('%Y%m%d%H%M%S')}-{len(request.party_codes)}"

        async def _delayed_send():
            delay_seconds = max(0.0, (schedule_for - datetime.now(schedule_for.tzinfo)).total_seconds())
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            try:
                await reminder_service.send_reminders_to_parties(
                    party_codes=request.party_codes,
                    template_id=request.template_id,
                    sent_by="scheduled",
                    company_id=company_id
                )
            except Exception as e:
                logger.error("scheduled_batch_execution_failed", batch_id=batch_id, error=str(e), exc_info=True)

        asyncio.create_task(_delayed_send())

        return {
            "status": "scheduled",
            "batch_id": batch_id,
            "scheduled_for": request.schedule_for,
            "message": f"Reminders scheduled for {len(request.party_codes)} parties"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("schedule_reminders_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batches/{batch_id}/cancel")
async def cancel_batch(batch_id: str):
    """Cancel a scheduled batch (not yet implemented)"""
    # TODO: Implement batch cancellation
    raise HTTPException(status_code=501, detail="Batch cancellation not yet implemented")


@router.get("/batches/recent")
async def list_recent_batches(limit: int = Query(20, ge=1, le=200)):
    """List recent reminder batch reports."""
    try:
        batches = await reminder_service.list_recent_batches(limit=limit)
        return {"items": batches, "total": len(batches), "limit": limit}
    except Exception as e:
        logger.error("list_recent_batches_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches/{batch_id}/report")
async def get_batch_report(batch_id: str):
    """Get reminder batch report summary with recipient details."""
    try:
        report = await reminder_service.get_batch_report(batch_id)
        if not report:
            raise HTTPException(status_code=404, detail="Batch report not found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_batch_report_error", batch_id=batch_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches/{batch_id}/failures")
async def get_batch_failures(
    batch_id: str,
    failure_stage: Optional[str] = Query(None),
    failure_code: Optional[str] = Query(None),
):
    """Get failed recipients for a batch with optional filters."""
    try:
        rows = await reminder_service.get_batch_failures(
            batch_id=batch_id,
            failure_stage=failure_stage,
            failure_code=failure_code,
        )
        return {"items": rows, "total": len(rows)}
    except Exception as e:
        logger.error("get_batch_failures_error", batch_id=batch_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Template Management Endpoints
# ============================================

@router.get("/templates", response_model=List[MessageTemplate])
async def list_templates(company_id: str = Depends(get_company_id)):
    """Get all message templates"""
    try:
        templates = reminder_config_service.get_all_templates(scope_key=company_id)
        return templates
        
    except Exception as e:
        logger.error("list_templates_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}", response_model=MessageTemplate)
async def get_template(template_id: str, company_id: str = Depends(get_company_id)):
    """Get a specific template by ID"""
    try:
        template = reminder_config_service.get_template(template_id, scope_key=company_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        return template
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates")
async def create_template(template: MessageTemplate, company_id: str = Depends(get_company_id)):
    """Create a new message template"""
    try:
        reminder_config_service.add_template(template, scope_key=company_id)
        return {
            "status": "success",
            "template": template,
            "message": "Template created successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("create_template_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/templates/{template_id}")
async def update_template(template_id: str, template: MessageTemplate, company_id: str = Depends(get_company_id)):
    """Update an existing template"""
    try:
        reminder_config_service.update_template(template_id, template, scope_key=company_id)
        return {
            "status": "success",
            "template": template,
            "message": "Template updated successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("update_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, company_id: str = Depends(get_company_id)):
    """Delete a template"""
    try:
        reminder_config_service.delete_template(template_id, scope_key=company_id)
        return {
            "status": "success",
            "message": f"Template {template_id} deleted"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("delete_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}/default")
async def set_default_template(template_id: str, company_id: str = Depends(get_company_id)):
    """Set a template as the default template"""
    try:
        reminder_config_service.set_active_template(template_id, scope_key=company_id)
        return {
            "status": "success",
            "message": f"Template {template_id} set as default"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("set_default_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}/preview")
async def preview_template(
    template_id: str,
    request: PreviewTemplateRequest,
    company_id: str = Depends(get_company_id)
):
    """Preview a template with sample data"""
    try:
        # Use provided variables or defaults
        variables = request.variables or template_service.get_default_variables()
        
        template = reminder_config_service.get_template(template_id, scope_key=company_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        preview = template_service.render_template(template, variables)
        
        return {
            "template_id": template_id,
            "preview": preview,
            "variables_used": list(variables.keys())
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("preview_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}/active")
async def set_active_template(template_id: str, company_id: str = Depends(get_company_id)):
    """Set a template as the active (default) template"""
    try:
        reminder_config_service.set_active_template(template_id, scope_key=company_id)
        return {
            "status": "success",
            "message": f"Template {template_id} is now active"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("set_active_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Company Settings Endpoints
# ============================================

@router.get("/config/company")
async def get_company_settings(company_id: str = Depends(get_company_id)):
    """Get company settings (name, contact phone, etc.)"""
    try:
        config = reminder_config_service.get_config(scope_key=company_id)
        return {
            "name": config.company.name,
            "contact_phone": config.company.contact_phone,
            "address": config.company.address
        }
    except Exception as e:
        logger.error("get_company_settings_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/company")
async def update_company_settings(settings: dict, company_id: str = Depends(get_company_id)):
    """Update company settings"""
    try:
        from app.models.reminder_schemas import CompanySettings
        
        config = reminder_config_service.get_config(scope_key=company_id)
        config.company = CompanySettings(
            name=settings.get("name", config.company.name),
            contact_phone=settings.get("contact_phone", config.company.contact_phone),
            address=settings.get("address", config.company.address)
        )
        reminder_config_service.save_config(config, scope_key=company_id)
        
        logger.info("company_settings_updated", name=config.company.name)
        return {
            "status": "success",
            "message": "Company settings updated",
            "settings": {
                "name": config.company.name,
                "contact_phone": config.company.contact_phone,
                "address": config.company.address
            }
        }
    except Exception as e:
        logger.error("update_company_settings_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/currency")
async def get_currency_settings(company_id: str = Depends(get_company_id)):
    """Get currency settings"""
    try:
        config = reminder_config_service.get_config(scope_key=company_id)
        return {
            "currency_symbol": config.currency_symbol
        }
    except Exception as e:
        logger.error("get_currency_settings_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/currency")
async def update_currency_settings(settings: dict, company_id: str = Depends(get_company_id)):
    """Update currency settings"""
    try:
        config = reminder_config_service.get_config(scope_key=company_id)
        if "currency_symbol" in settings:
            config.currency_symbol = settings["currency_symbol"]
        reminder_config_service.save_config(config, scope_key=company_id)
        
        logger.info("currency_settings_updated", symbol=config.currency_symbol)
        return {
            "status": "success",
            "message": "Currency settings updated",
            "settings": {
                "currency_symbol": config.currency_symbol
            }
        }
    except Exception as e:
        logger.error("update_currency_settings_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Anti-Spam Configuration Endpoints
# ============================================

@router.get("/antispam/config")
async def get_antispam_config():
    """Get anti-spam configuration"""
    try:
        config = anti_spam_service.get_config()
        return {
            "enabled": config.enabled,
            "message_inflation": config.message_inflation,
            "pdf_inflation": config.pdf_inflation,
            "typing_simulation": config.typing_simulation,
            "startup_delay_enabled": True,  # Always enabled when anti-spam is on
            "reminder_cooldown_enabled": config.reminder_cooldown_enabled,
            "reminder_cooldown_minutes": config.reminder_cooldown_minutes,
        }
    except Exception as e:
        logger.error("get_antispam_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/antispam/config")
async def update_antispam_config(config_update: dict):
    """Update anti-spam configuration"""
    try:
        from app.services.anti_spam_service import AntiSpamConfig
        
        current_config = anti_spam_service.get_config()
        # Merge current with update and validate via Pydantic
        current_data = current_config.model_dump()
        current_data.update(config_update)
        
        new_config = AntiSpamConfig(**current_data)
        anti_spam_service.update_config(new_config)
        
        logger.info("antispam_config_updated", config=new_config.model_dump())
        return {"status": "success", "message": "Anti-spam configuration updated"}
    except Exception as e:
        logger.error("update_antispam_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Session Control Endpoints
# ============================================

@router.post("/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    """Pause an active reminder session"""
    try:
        success = await reminder_service.pause_session(session_id)
        if success:
            return {"status": "success", "message": "Session paused"}
        else:
            raise HTTPException(status_code=404, detail="Session not found or already completed")
    except Exception as e:
        logger.error("pause_session_error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    """Resume a paused reminder session"""
    try:
        success = await reminder_service.resume_session(session_id)
        if success:
            return {"status": "success", "message": "Session resumed"}
        else:
            raise HTTPException(status_code=404, detail="Session not found or not paused")
    except Exception as e:
        logger.error("resume_session_error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop an active reminder session"""
    try:
        success = await reminder_service.stop_session(session_id)
        if success:
            return {"status": "success", "message": "Session stopped"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error("stop_session_error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get status of a reminder session"""
    try:
        status = await reminder_service.get_session_status(session_id)
        if status:
            return status
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_session_status_error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/active")
async def get_active_sessions():
    """Get all active reminder sessions"""
    try:
        sessions = await reminder_service.get_active_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.error("get_active_sessions_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Statistics Endpoints
# ============================================

@router.get("/stats", response_model=ReminderStats)
async def get_reminder_stats(company_id: str = Depends(get_company_id)):
    """Get reminder system statistics"""
    try:
        stats = await reminder_service.get_stats(company_id=company_id)
        return stats
        
    except Exception as e:
        logger.error("get_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_reminder_history(
    status: Optional[str] = Query(None, description="Filter by status (sent/failed)"),
    delivery_status: Optional[str] = Query(None, description="Filter by delivery status (accepted/sent/delivered/read/failed)"),
    from_time: Optional[datetime] = Query(None, description="Filter completed_at >= from_time (ISO datetime)"),
    to_time: Optional[datetime] = Query(None, description="Filter completed_at <= to_time (ISO datetime)"),
    limit: int = Query(100, description="Number of records to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get reminder sending history"""
    from app.database.message_queue import message_db

    items = message_db.get_message_history(
        source="payment_reminder",
        status=status,
        delivery_status=delivery_status,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        offset=offset,
    )
    total = message_db.count_message_history(
        source="payment_reminder",
        status=status,
        delivery_status=delivery_status,
        from_time=from_time,
        to_time=to_time,
    )
    totals = message_db.get_message_counts_by_source(source="payment_reminder")

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "counts": totals,
    }


@router.get("/history/export")
async def export_reminder_history():
    """Export reminder history as CSV"""
    # TODO: Implement CSV export
    raise HTTPException(status_code=501, detail="Export not yet implemented")
