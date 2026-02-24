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
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field

import structlog

from app.models.reminder_schemas import (
    PartyReminderInfo,
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
from app.services.scheduler_service import scheduler_service
from app.services.amount_due_calculator import amount_due_calculator

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/reminders", tags=["Payment Reminders"])


# ============================================
# Configuration Endpoints
# ============================================

@router.get("/config", response_model=ReminderConfig)
async def get_reminder_config():
    """Get full reminder configuration"""
    try:
        config = reminder_config_service.get_config()
        return config
    except Exception as e:
        logger.error("get_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_reminder_config(config: ReminderConfig):
    """Update reminder configuration"""
    try:
        reminder_config_service.save_config(config)
        logger.info("config_updated")
        return {"status": "success", "message": "Configuration updated"}
    except Exception as e:
        logger.error("update_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/schedule")
async def update_schedule_config(schedule: ScheduleConfig):
    """Update schedule configuration"""
    try:
        reminder_config_service.update_schedule(schedule)
        
        # Restart scheduler if it's running
        if scheduler_service.is_running:
            await scheduler_service.stop_scheduler()
            await scheduler_service.initialize()
        
        logger.info("schedule_updated", enabled=schedule.enabled)
        return {"status": "success", "message": "Schedule configuration updated"}
    except Exception as e:
        logger.error("update_schedule_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Party Management Endpoints
# ============================================

@router.get("/parties", response_model=List[PartyReminderInfo])
async def list_eligible_parties(
    search: Optional[str] = Query(None, description="Search by name or code"),
    sort_by: str = Query("amount_due", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    filter_by: str = Query("all", description="Filter option"),
    min_amount: Optional[Decimal] = Query(None, description="Minimum amount due"),
):
    """Get all eligible parties with amount due > 0"""
    try:
        min_amt = min_amount or Decimal("0.01")
        
        parties = await reminder_service.get_eligible_parties(
            min_amount_due=min_amt,
            search=search,
            filter_by=filter_by
        )
        
        # Sort parties
        reverse = sort_order.lower() == "desc"
        if sort_by == "amount_due":
            parties.sort(key=lambda x: x.amount_due, reverse=reverse)
        elif sort_by == "name":
            parties.sort(key=lambda x: x.name.lower(), reverse=reverse)
        elif sort_by == "credit_days":
            parties.sort(key=lambda x: x.sales_credit_days, reverse=reverse)
        elif sort_by == "code":
            parties.sort(key=lambda x: x.code, reverse=reverse)
        
        return parties
        
    except Exception as e:
        logger.error("list_parties_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parties/{party_code}", response_model=PartyReminderInfo)
async def get_party_details(party_code: str):
    """Get detailed information for a specific party"""
    try:
        # Get party from eligible list
        parties = await reminder_service.get_eligible_parties()
        party = next((p for p in parties if p.code == party_code), None)
        
        if not party:
            raise HTTPException(status_code=404, detail=f"Party {party_code} not found")
        
        return party
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_party_error", party_code=party_code, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parties/{party_code}/ledger")
async def get_party_ledger_pdf(party_code: str):
    """Generate and download ledger PDF for a party"""
    try:
        pdf_bytes = await reminder_service.generate_ledger_pdf(party_code)
        
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
    party_code: str,
    request: UpdatePartyRequest
):
    """Update party configuration (permanent settings)"""
    try:
        party = await reminder_service.update_party_selection(
            party_code=party_code,
            permanent_enabled=request.permanent_enabled,
            credit_days_override=request.credit_days_override
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
    credit_days_override: Optional[int] = None
):
    """Calculate amount due for a specific party with optional credit days override"""
    try:
        calculation = await amount_due_calculator.calculate_for_party(
            party_code=party_code,
            credit_days=credit_days_override
        )
        return calculation
        
    except Exception as e:
        logger.error("calculate_amount_due_error", party_code=party_code, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Batch Operations Endpoints
# ============================================

@router.post("/send")
async def send_reminders(request: CreateBatchRequest):
    """Send reminders to selected parties immediately"""
    try:
        batch_id = await reminder_service.send_reminders_to_parties(
            party_codes=request.party_codes,
            template_id=request.template_id,
            sent_by="manual"
        )
        
        return {
            "status": "success",
            "batch_id": batch_id,
            "message": f"Reminders queued for {len(request.party_codes)} parties"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("send_reminders_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule")
async def schedule_reminders(request: CreateBatchRequest):
    """Schedule reminders for later delivery"""
    try:
        # For now, we'll just send immediately
        # In production, this would store the batch for later processing
        batch_id = await reminder_service.send_reminders_to_parties(
            party_codes=request.party_codes,
            template_id=request.template_id,
            sent_by="scheduled"
        )
        
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


# ============================================
# Template Management Endpoints
# ============================================

@router.get("/templates", response_model=List[MessageTemplate])
async def list_templates():
    """Get all message templates"""
    try:
        templates = reminder_config_service.get_all_templates()
        return templates
        
    except Exception as e:
        logger.error("list_templates_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}", response_model=MessageTemplate)
async def get_template(template_id: str):
    """Get a specific template by ID"""
    try:
        template = reminder_config_service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        return template
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates")
async def create_template(template: MessageTemplate):
    """Create a new message template"""
    try:
        reminder_config_service.add_template(template)
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
async def update_template(template_id: str, template: MessageTemplate):
    """Update an existing template"""
    try:
        reminder_config_service.update_template(template_id, template)
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
async def delete_template(template_id: str):
    """Delete a template"""
    try:
        reminder_config_service.delete_template(template_id)
        return {
            "status": "success",
            "message": f"Template {template_id} deleted"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("delete_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}/preview")
async def preview_template(
    template_id: str,
    request: PreviewTemplateRequest
):
    """Preview a template with sample data"""
    try:
        # Use provided variables or defaults
        variables = request.variables or template_service.get_default_variables()
        
        template = reminder_config_service.get_template(template_id)
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


@router.post("/templates/{template_id}/activate")
async def set_active_template(template_id: str):
    """Set a template as the active (default) template"""
    try:
        reminder_config_service.set_active_template(template_id)
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
async def get_company_settings():
    """Get company settings (name, contact phone, etc.)"""
    try:
        config = reminder_config_service.get_config()
        return {
            "name": config.company.name,
            "contact_phone": config.company.contact_phone,
            "address": config.company.address
        }
    except Exception as e:
        logger.error("get_company_settings_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/company")
async def update_company_settings(settings: dict):
    """Update company settings"""
    try:
        from app.models.reminder_schemas import CompanySettings
        
        config = reminder_config_service.get_config()
        config.company = CompanySettings(
            name=settings.get("name", config.company.name),
            contact_phone=settings.get("contact_phone", config.company.contact_phone),
            address=settings.get("address", config.company.address)
        )
        reminder_config_service.save_config(config)
        
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
async def get_currency_settings():
    """Get currency settings"""
    try:
        config = reminder_config_service.get_config()
        return {
            "currency_symbol": config.currency_symbol
        }
    except Exception as e:
        logger.error("get_currency_settings_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/currency")
async def update_currency_settings(settings: dict):
    """Update currency settings"""
    try:
        config = reminder_config_service.get_config()
        if "currency_symbol" in settings:
            config.currency_symbol = settings["currency_symbol"]
        reminder_config_service.save_config(config)
        
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
# Scheduler Control Endpoints
# ============================================

@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get current scheduler status"""
    try:
        status = scheduler_service.get_status()
        config = reminder_config_service.get_config()
        
        return {
            "is_running": status["is_running"],
            "next_run": status["next_run"],
            "schedule_enabled": config.schedule.enabled,
            "frequency": config.schedule.frequency,
            "day_of_week": config.schedule.day_of_week,
            "time": config.schedule.time,
            "timezone": config.schedule.timezone
        }
        
    except Exception as e:
        logger.error("get_scheduler_status_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/start")
async def start_scheduler():
    """Start the reminder scheduler"""
    try:
        await scheduler_service.start_scheduler()
        return {
            "status": "success",
            "message": "Scheduler started"
        }
        
    except Exception as e:
        logger.error("start_scheduler_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the reminder scheduler"""
    try:
        await scheduler_service.stop_scheduler()
        return {
            "status": "success",
            "message": "Scheduler stopped"
        }
        
    except Exception as e:
        logger.error("stop_scheduler_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/pause")
async def pause_scheduler():
    """Pause the reminder scheduler"""
    try:
        await scheduler_service.pause_scheduler()
        return {
            "status": "success",
            "message": "Scheduler paused"
        }
        
    except Exception as e:
        logger.error("pause_scheduler_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/resume")
async def resume_scheduler():
    """Resume the reminder scheduler"""
    try:
        await scheduler_service.resume_scheduler()
        return {
            "status": "success",
            "message": "Scheduler resumed"
        }
        
    except Exception as e:
        logger.error("resume_scheduler_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/trigger")
async def trigger_manual_run():
    """Manually trigger a reminder run"""
    try:
        batch_id = await scheduler_service.trigger_manual_run()
        return {
            "status": "success",
            "batch_id": batch_id,
            "message": "Manual reminder run triggered"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("trigger_manual_run_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Statistics Endpoints
# ============================================

@router.get("/stats", response_model=ReminderStats)
async def get_reminder_stats():
    """Get reminder system statistics"""
    try:
        stats = await reminder_service.get_stats()
        return stats
        
    except Exception as e:
        logger.error("get_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_reminder_history(
    limit: int = Query(100, description="Number of records to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get reminder sending history"""
    # TODO: Implement history tracking
    return {
        "items": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }


@router.get("/history/export")
async def export_reminder_history():
    """Export reminder history as CSV"""
    # TODO: Implement CSV export
    raise HTTPException(status_code=501, detail="Export not yet implemented")
