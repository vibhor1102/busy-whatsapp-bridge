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
import hashlib
import os
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
from app.database.reminder_snapshot import reminder_snapshot_db
from app.config import get_local_appdata_path, get_settings
from app.services.reminder_snapshot_service import reminder_snapshot_service
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
        self.snapshot_db = reminder_snapshot_db
        self.snapshot_service = reminder_snapshot_service
        self._ledger_dir = get_local_appdata_path() / "data" / "reminder_ledgers"
        self._ledger_dir.mkdir(parents=True, exist_ok=True)
        self._settings = get_settings()

    def _resolve_delivery_provider(self, configured_provider: Optional[str]) -> str:
        """
        Resolve effective provider for reminder dispatch with safe fallbacks.

        If Meta is selected without webhook status tracking, fallback to runtime
        provider (typically Baileys) to avoid false-positive "accepted" sends.
        """
        provider = (configured_provider or "baileys").strip().lower()
        if provider != "meta":
            return provider

        webhook_ready = bool(self._settings.META_WEBHOOK_VERIFY_TOKEN)
        if webhook_ready:
            return "meta"

        fallback = (self._settings.WHATSAPP_PROVIDER or "baileys").strip().lower()
        if fallback == "meta":
            fallback = "baileys"

        logger.warning(
            "reminder_provider_fallback",
            configured_provider=provider,
            effective_provider=fallback,
            reason="meta_webhook_not_configured",
        )
        return fallback

    def get_snapshot_status(self) -> Dict[str, Any]:
        """Return current snapshot metadata."""
        return self.snapshot_db.get_status()

    def refresh_snapshot(self) -> Dict[str, Any]:
        """Recompute and persist reminder snapshot on demand."""
        return self.snapshot_service.refresh_snapshot()

    def get_eligible_parties_page(
        self,
        *,
        min_amount_due: Decimal = Decimal("0.01"),
        search: Optional[str] = None,
        filter_by: str = "all",
        include_zero: bool = False,
        sort_by: str = "amount_due",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get paginated parties from snapshot with server-side filters/sorting."""
        snap_status = self.snapshot_db.get_status()
        current_hash = hashlib.sha256(
            ((self.calculator.db.settings.BDS_FILE_PATH or "").encode("utf-8"))
        ).hexdigest()
        snap_hash = snap_status.get("source_db_path_hash")

        # Snapshot must be explicitly refreshed if data source path changed.
        if snap_status.get("has_snapshot") and snap_hash and snap_hash != current_hash:
            logger.warning(
                "reminder_snapshot_stale_db_path_changed",
                snapshot_hash=snap_hash,
                current_hash=current_hash,
            )
            return {
                "items": [],
                "total": 0,
                "offset": int(offset),
                "limit": int(limit),
                "has_more": False,
            }

        total, rows = self.snapshot_db.query_parties(
            search=search,
            filter_by=filter_by,
            min_amount=float(min_amount_due) if min_amount_due is not None else None,
            include_zero=include_zero,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=max(0, int(offset)),
            limit=max(1, int(limit)),
        )
        config = self.config_service.get_config()
        currency = config.currency_symbol

        items: List[PartyReminderInfo] = []
        for r in rows:
            items.append(
                PartyReminderInfo(
                    code=str(r["party_code"]),
                    name=r["name"],
                    print_name=r.get("print_name"),
                    phone=r.get("phone"),
                    closing_balance=Decimal(str(r.get("closing_balance") or 0)),
                    closing_balance_formatted=f"{currency}{Decimal(str(r.get('closing_balance') or 0)):,.2f}",
                    amount_due=Decimal(str(r.get("amount_due") or 0)),
                    amount_due_formatted=f"{currency}{Decimal(str(r.get('amount_due') or 0)):,.2f}",
                    sales_credit_days=int(r.get("sales_credit_days") or self.calculator.default_credit_days),
                    credit_days_source=str(r.get("credit_days_source") or "config_default"),
                    permanent_enabled=bool(r.get("permanent_enabled")),
                    temp_enabled=False,
                )
            )

        return {
            "items": items,
            "total": int(total),
            "offset": int(offset),
            "limit": int(limit),
            "has_more": int(offset) + len(items) < int(total),
        }
    
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
        
        page = self.get_eligible_parties_page(
            min_amount_due=min_amount_due,
            search=search,
            filter_by=filter_by,
            include_zero=False,
            sort_by="amount_due",
            sort_order="desc",
            offset=0,
            limit=limit,
        )
        parties = page["items"]
        
        logger.info(
            "eligible_parties_fetched",
            total_count=len(parties),
            filter_by=filter_by,
            limit=limit
        )
        
        return parties

    async def get_party_info(self, party_code: str) -> PartyReminderInfo:
        """Get a single party reminder info payload by party code."""
        calculation = await self.calculator.calculate_for_party(party_code)
        customer = ledger_data_service.get_customer_info(party_code)

        config = self.config_service.get_config()
        currency = config.currency_symbol
        party_config = config.parties.get(party_code)

        party = PartyReminderInfo(
            code=party_code,
            name=customer.name,
            print_name=customer.print_name,
            phone=customer.phone,
            closing_balance=calculation.closing_balance,
            closing_balance_formatted=f"{currency}{calculation.closing_balance:,.2f}",
            amount_due=calculation.amount_due,
            amount_due_formatted=f"{currency}{calculation.amount_due:,.2f}",
            sales_credit_days=calculation.credit_days_used,
            credit_days_source=calculation.credit_days_source,
            permanent_enabled=bool(party_config.enabled) if party_config else False,
            temp_enabled=False,
        )
        return party
    
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
        
        if permanent_enabled is not None:
            self.snapshot_db.update_party_permanent_enabled(party_code, permanent_enabled)

        # Re-fetch directly by code from snapshot first.
        page = self.get_eligible_parties_page(
            min_amount_due=Decimal("-999999999"),
            search=party_code,
            filter_by="all",
            include_zero=True,
            sort_by="code",
            sort_order="asc",
            offset=0,
            limit=5,
        )
        party = next((p for p in page["items"] if p.code == party_code), None)
        
        if party is None:
            # Fallback to direct per-party calculation if snapshot does not have it.
            party = await self.get_party_info(party_code)
        
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
            
            # Generate PDF to disk, then read bytes for API response.
            pdf_path = self._ledger_dir / f"ledger_{party_code}_preview.pdf"
            ledger_pdf_service.generate(report=report, output_path=str(pdf_path))

            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

            logger.info(
                "ledger_pdf_generated",
                party_code=party_code,
                output_path=str(pdf_path),
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
                        provider = self._resolve_delivery_provider(config.default_provider)
                        # Persist locally so retries still have access to media.
                        pdf_path = str(self._ledger_dir / f"ledger_{party_code}_{batch_id}.pdf")
                        with open(pdf_path, 'wb') as f:
                            f.write(pdf_bytes)

                        # Local media is supported for Baileys/Evolution and uploaded
                        # on-demand for Meta in MetaProvider.
                        media_ref = pdf_path if provider in {"baileys", "evolution", "meta"} else None
                        if media_ref is None:
                            logger.warning(
                                "reminder_media_not_supported_for_provider",
                                provider=provider,
                                party_code=party_code,
                            )

                        message_db.enqueue_message(
                            phone=party_info.phone,
                            message=message,
                            pdf_url=media_ref,
                            provider=provider,
                            source="payment_reminder"
                        )
                        
                        results[party_code] = {
                            "status": "queued",
                            "phone": party_info.phone,
                            "amount_due": str(calculation.amount_due),
                            "media_attached": bool(media_ref),
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
        snap = self.snapshot_db.get_status()
        page = self.get_eligible_parties_page(
            min_amount_due=Decimal("0.01"),
            include_zero=False,
            filter_by="all",
            offset=0,
            limit=100000,
        )
        eligible_parties = page["items"]
        enabled_count = sum(1 for p in eligible_parties if p.permanent_enabled)
        total_due = sum((p.amount_due for p in eligible_parties), Decimal("0"))
        avg_due = total_due / len(eligible_parties) if eligible_parties else Decimal("0")
        
        # Get scheduler status
        from app.services.scheduler_service import scheduler_service
        scheduler_status = scheduler_service.get_status()
        
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        today_counts = message_db.get_message_counts_by_source(
            source="payment_reminder",
            start_date=today_start,
        )
        week_counts = message_db.get_message_counts_by_source(
            source="payment_reminder",
            start_date=week_start,
        )
        month_counts = message_db.get_message_counts_by_source(
            source="payment_reminder",
            start_date=month_start,
        )

        try:
            total_parties = int(snap.get("row_count") or self.calculator.get_debtor_party_count())
        except Exception:
            total_parties = 0

        last_scheduler_run = None
        if hasattr(scheduler_service, "get_last_run_time"):
            last_scheduler_run = scheduler_service.get_last_run_time()

        return ReminderStats(
            total_parties=total_parties,
            eligible_parties=len(eligible_parties),
            enabled_parties=enabled_count,
            reminders_sent_today=today_counts.get("sent", 0),
            reminders_sent_this_week=week_counts.get("sent", 0),
            reminders_sent_this_month=month_counts.get("sent", 0),
            total_amount_due=total_due,
            average_amount_due=avg_due,
            last_scheduler_run=last_scheduler_run,
            next_scheduler_run=scheduler_status.get("next_run"),
            scheduler_status="running" if scheduler_status.get("is_running") else "stopped"
        )


# Global instance
reminder_service = ReminderService()
