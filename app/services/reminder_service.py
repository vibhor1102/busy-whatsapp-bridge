"""
Reminder Service - Main Orchestrator

Coordinates all reminder operations including:
- Calculating amount due for parties
- Managing party selection and configuration
- Sending reminders in batches
- Generating ledger PDFs
- Tracking reminder history
"""
import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

import structlog

from app.models.reminder_schemas import (
    PartyReminderInfo,
    ReminderConfig,
    PartyConfig,
    MessageTemplate,
    ReminderBatch,
    ReminderStats,
)
from app.services.amount_due_calculator import amount_due_calculator
from app.services.reminder_config_service import reminder_config_service
from app.services.template_service import template_service
from app.services.ledger_data_service import ledger_data_service
from app.services.ledger_pdf_service import ledger_pdf_service
from app.database.message_queue import message_db
from app.constants.reminder_constants import (
    REMINDER_STATUS_COMPLETED,
    REMINDER_STATUS_FAILED,
    REMINDER_STATUS_SENDING,
    CURRENCY_SYMBOL,
)

logger = structlog.get_logger()


class ReminderService:
    """Main service for payment reminders"""
    
    def __init__(self):
        self.calculator = amount_due_calculator
        self.config_service = reminder_config_service
        self.template_svc = template_service
    
    async def get_eligible_parties(
        self,
        min_amount_due: Decimal = Decimal("0.01"),
        search: Optional[str] = None,
        filter_by: str = "all",
        limit: int = 50
    ) -> List[PartyReminderInfo]:
        """
        Get all parties eligible for reminders (amount_due > 0)
        
        Args:
            min_amount_due: Minimum amount due threshold
            search: Optional search term for party name/code
            filter_by: Filter option (all, enabled, disabled, etc.)
            
        Returns:
            List of PartyReminderInfo sorted by amount due (desc)
        """
        logger.info(
            "fetching_eligible_parties",
            min_amount_due=min_amount_due,
            filter_by=filter_by
        )
        
        # Calculate amount due for all parties
        parties = await self.calculator.calculate_for_all_parties(
            min_amount_due=min_amount_due,
            max_parties=max(1, min(int(limit), 2000))
        )
        
        # Enrich with config data
        config = self.config_service.get_config()
        
        for party in parties:
            party_config = config.parties.get(party.code)
            if party_config:
                party.permanent_enabled = party_config.enabled
                # Apply credit days override if exists
                if party_config.credit_days_override:
                    party.sales_credit_days = party_config.credit_days_override
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            parties = [
                p for p in parties
                if (search_lower in p.name.lower() or
                    search_lower in p.code.lower() or
                    (p.phone and search_lower in p.phone.lower()))
            ]
        
        # Apply status filter
        if filter_by == "enabled":
            parties = [p for p in parties if p.permanent_enabled]
        elif filter_by == "disabled":
            parties = [p for p in parties if not p.permanent_enabled]
        
        logger.info(
            "eligible_parties_fetched",
            total_count=len(parties),
            filter_by=filter_by,
            limit=limit
        )
        
        return parties
    
    async def update_party_selection(
        self,
        party_code: str,
        temp_enabled: Optional[bool] = None,
        permanent_enabled: Optional[bool] = None,
        credit_days_override: Optional[int] = None
    ) -> PartyReminderInfo:
        """
        Update party selection/configuration
        
        Args:
            party_code: Party code to update
            temp_enabled: Temporary selection (current batch only)
            permanent_enabled: Permanent selection (saved to config)
            credit_days_override: Override credit days for this party
            
        Returns:
            Updated PartyReminderInfo
        """
        logger.info(
            "updating_party_selection",
            party_code=party_code,
            permanent_enabled=permanent_enabled
        )
        
        # Get current party info
        calculation = await self.calculator.calculate_for_party(party_code)
        
        # Update permanent config if provided
        if permanent_enabled is not None or credit_days_override is not None:
            party_config = self.config_service.get_party_config(party_code)
            
            if party_config is None:
                party_config = PartyConfig()
            
            if permanent_enabled is not None:
                party_config.enabled = permanent_enabled
            
            if credit_days_override is not None:
                party_config.credit_days_override = credit_days_override
            
            self.config_service.update_party_config(party_code, party_config)
        
        # Re-fetch to get updated data
        parties = await self.get_eligible_parties(limit=100)
        party = next((p for p in parties if p.code == party_code), None)
        
        if party is None:
            raise ValueError(f"Party {party_code} not found or not eligible")
        
        # Update temp selection if provided
        if temp_enabled is not None:
            party.temp_enabled = temp_enabled
        
        return party
    
    async def generate_ledger_pdf(self, party_code: str) -> bytes:
        """
        Generate ledger PDF for a party
        
        Args:
            party_code: Party code
            
        Returns:
            PDF bytes
        """
        logger.info("generating_ledger_pdf", party_code=party_code)
        
        try:
            # Generate ledger report
            report = ledger_data_service.generate_ledger_report(party_code)
            
            # Generate PDF
            pdf_bytes = ledger_pdf_service.generate_pdf(report)
            
            logger.info(
                "ledger_pdf_generated",
                party_code=party_code,
                size_bytes=len(pdf_bytes)
            )
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(
                "ledger_pdf_generation_failed",
                party_code=party_code,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def send_reminders_to_parties(
        self,
        party_codes: List[str],
        template_id: str,
        sent_by: str = "manual",
        schedule_delay: Optional[int] = None
    ) -> str:
        """
        Send reminders to selected parties
        
        Args:
            party_codes: List of party codes to send to
            template_id: Template ID to use
            sent_by: Who triggered the send ("manual" or "scheduler")
            schedule_delay: Delay in seconds before sending (None = immediate)
            
        Returns:
            Batch ID
        """
        batch_id = str(uuid.uuid4())
        
        logger.info(
            "sending_reminders",
            batch_id=batch_id,
            party_count=len(party_codes),
            template_id=template_id,
            sent_by=sent_by
        )
        
        try:
            # Get template
            template = self.config_service.get_template(template_id)
            if template is None:
                raise ValueError(f"Template '{template_id}' not found")
            
            # Create batch record
            batch = ReminderBatch(
                batch_id=batch_id,
                template_id=template_id,
                party_count=len(party_codes),
                parties=party_codes,
                status=REMINDER_STATUS_SENDING
            )
            
            # Process each party
            results = {}
            config = self.config_service.get_config()
            
            for i, party_code in enumerate(party_codes):
                try:
                    # Calculate amount due
                    calculation = await self.calculator.calculate_for_party(party_code)
                    
                    if calculation.amount_due <= 0:
                        results[party_code] = {
                            "status": "skipped",
                            "reason": "amount_due_not_positive"
                        }
                        continue
                    
                    # Generate ledger PDF
                    pdf_bytes = await self.generate_ledger_pdf(party_code)
                    
                    # Save PDF temporarily (in production, use temp file or cloud storage)
                    # For now, we'll attach it directly to the message
                    
                    # Get party info
                    party_info = ledger_data_service.get_customer_info(party_code)
                    
                    # Render message
                    variables = self.template_svc.get_template_variables(
                        party_code=party_code,
                        amount_due=float(calculation.amount_due)
                    )
                    message = self.template_svc.render_template(template, variables)
                    
                    # Queue message
                    if party_info.phone:
                        # Save PDF to temp location
                        temp_dir = tempfile.gettempdir()
                        pdf_path = os.path.join(temp_dir, f"ledger_{party_code}_{batch_id}.pdf")
                        with open(pdf_path, 'wb') as f:
                            f.write(pdf_bytes)
                        
                        # Queue for sending
                        try:
                            message_db.enqueue_message(
                                phone=party_info.phone,
                                message=message,
                                pdf_path=pdf_path,
                                provider=config.default_provider,
                                source="payment_reminder"
                            )
                        finally:
                            # Clean up temp file after queuing
                            try:
                                if os.path.exists(pdf_path):
                                    os.remove(pdf_path)
                            except Exception as cleanup_error:
                                logger.warning("failed_to_cleanup_temp_pdf", 
                                             path=pdf_path, error=str(cleanup_error))
                        
                        results[party_code] = {
                            "status": "queued",
                            "phone": party_info.phone,
                            "amount_due": str(calculation.amount_due)
                        }
                        
                        logger.info(
                            "reminder_queued",
                            party_code=party_code,
                            batch_id=batch_id
                        )
                    else:
                        results[party_code] = {
                            "status": "failed",
                            "reason": "no_phone_number"
                        }
                    
                    # Add delay between messages
                    if i < len(party_codes) - 1:
                        await asyncio.sleep(config.schedule.delay_between_messages)
                        
                except Exception as e:
                    logger.error(
                        "reminder_send_failed",
                        party_code=party_code,
                        batch_id=batch_id,
                        error=str(e)
                    )
                    results[party_code] = {
                        "status": "failed",
                        "error": str(e)
                    }
            
            # Update batch status
            batch.status = REMINDER_STATUS_COMPLETED
            batch.results = results
            batch.sent_at = datetime.now()
            
            logger.info(
                "reminders_batch_completed",
                batch_id=batch_id,
                total=len(party_codes),
                successful=sum(1 for r in results.values() if r.get("status") == "queued"),
                failed=sum(1 for r in results.values() if r.get("status") == "failed")
            )
            
            return batch_id
            
        except Exception as e:
            logger.error(
                "send_reminders_failed",
                batch_id=batch_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def get_stats(self) -> ReminderStats:
        """Get reminder system statistics"""
        # Get all eligible parties
        eligible_parties = await self.get_eligible_parties(limit=100)
        
        # Count enabled parties
        enabled_count = sum(1 for p in eligible_parties if p.permanent_enabled)
        
        # Calculate total amount due
        total_due = sum(p.amount_due for p in eligible_parties)
        avg_due = total_due / len(eligible_parties) if eligible_parties else Decimal("0")
        
        # Get scheduler status
        from app.services.scheduler_service import scheduler_service
        scheduler_status = scheduler_service.get_status()
        
        # TODO: Get actual reminder counts from history
        # For now, return placeholder values
        
        return ReminderStats(
            total_parties=0,  # TODO: Get from database
            eligible_parties=len(eligible_parties),
            enabled_parties=enabled_count,
            reminders_sent_today=0,  # TODO: Query from history
            reminders_sent_this_week=0,
            reminders_sent_this_month=0,
            total_amount_due=total_due,
            average_amount_due=avg_due,
            last_scheduler_run=None,  # TODO: Track in scheduler
            next_scheduler_run=scheduler_status.get("next_run"),
            scheduler_status="running" if scheduler_status.get("is_running") else "stopped"
        )


# Global instance
reminder_service = ReminderService()
