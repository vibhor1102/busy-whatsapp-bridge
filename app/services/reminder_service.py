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
from app.services.anti_spam_service import anti_spam_service, ReminderSession, SessionState
from app.services.message_inflation_service import message_inflation_service
from app.services.pdf_inflation_service import pdf_inflation_service
from app.services.whatsapp import BaileysProvider
from app.database.message_queue import message_db
from app.database.reminder_snapshot import reminder_snapshot_db
from app.config import get_roaming_appdata_path, get_settings
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
        self._ledger_dir = get_roaming_appdata_path() / "data" / "reminder_ledgers"
        self._ledger_dir.mkdir(parents=True, exist_ok=True)
        self._settings = get_settings()

    def _resolve_delivery_provider(self, configured_provider: Optional[str]) -> str:
        """
        Resolve effective provider for reminder dispatch.
        
        NOTE: Previously this had fallback logic for Meta, Evolution, Webhook.
        Now only Baileys is available - all requests fall back to Baileys.
        TODO: Re-add other providers via Baileys integration when needed.
        """
        provider = (configured_provider or "baileys").strip().lower()
        
        # Only Baileys is available now - fallback all others to baileys
        if provider != "baileys":
            logger.warning(
                "reminder_provider_fallback",
                configured_provider=provider,
                effective_provider="baileys",
                message="Only Baileys provider available, using Baileys"
            )
            return "baileys"
        
        return provider

    def get_snapshot_status(self, company_id: str = "default") -> Dict[str, Any]:
        """Return current snapshot metadata."""
        return self.snapshot_db.get_status(company_id=company_id)

    def refresh_snapshot(self, company_id: str = "default") -> Dict[str, Any]:
        """Recompute and persist reminder snapshot on demand."""
        return self.snapshot_service.refresh_snapshot(company_id=company_id)

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
        company_id: str = "default",
    ) -> Dict[str, Any]:
        """Get paginated parties from snapshot with server-side filters/sorting."""
        snap_status = self.snapshot_db.get_status(company_id=company_id)
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
            company_id=company_id,
        )
        config = self.config_service.get_config(scope_key=company_id)
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
        limit: int = 50,
        company_id: str = "default",
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
            company_id=company_id,
        )
        parties = page["items"]
        
        logger.info(
            "eligible_parties_fetched",
            total_count=len(parties),
            filter_by=filter_by,
            limit=limit
        )
        
        return parties

    async def get_party_info(self, party_code: str, company_id: str = "default") -> PartyReminderInfo:
        """Get a single party reminder info payload by party code."""
        calculation = await self.calculator.calculate_for_party(party_code, company_id=company_id)
        customer = ledger_data_service.get_customer_info(party_code, company_id=company_id)

        config = self.config_service.get_config(scope_key=company_id)
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
        credit_days_override: Optional[int] = None,
        custom_template_id: Optional[str] = None,
        notes: Optional[str] = None,
        company_id: str = "default",
    ) -> PartyReminderInfo:
        """
        Update party selection/configuration
        
        Args:
            party_code: Party code to update
            temp_enabled: Temporary selection (current batch only)
            permanent_enabled: Permanent selection (saved to config)
            credit_days_override: Override credit days for this party
            custom_template_id: Custom template override for this party
            notes: Internal notes about this party

        Returns:
            Updated PartyReminderInfo
        """
        logger.info(
            "updating_party_selection",
            party_code=party_code,
            permanent_enabled=permanent_enabled,
            custom_template_id=custom_template_id,
        )

        needs_config_update = (
            permanent_enabled is not None
            or credit_days_override is not None
            or custom_template_id is not None
            or notes is not None
        )

        if needs_config_update:
            party_config = self.config_service.get_party_config(party_code, scope_key=company_id)

            if party_config is None:
                party_config = PartyConfig()

            if permanent_enabled is not None:
                party_config.enabled = permanent_enabled

            if credit_days_override is not None:
                party_config.credit_days_override = credit_days_override

            if custom_template_id is not None:
                party_config.custom_template_id = custom_template_id

            if notes is not None:
                party_config.notes = notes

            self.config_service.update_party_config(party_code, party_config, scope_key=company_id)
        
        if permanent_enabled is not None:
            self.snapshot_db.update_party_permanent_enabled(party_code, permanent_enabled, company_id=company_id)

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
            company_id=company_id,
        )
        party = next((p for p in page["items"] if p.code == party_code), None)
        
        if party is None:
            # Fallback to direct per-party calculation if snapshot does not have it.
            party = await self.get_party_info(party_code, company_id=company_id)
        
        # Update temp selection if provided
        if temp_enabled is not None:
            party.temp_enabled = temp_enabled
        
        return party
    
    async def generate_ledger_pdf(self, party_code: str, company_id: str = "default") -> bytes:
        """
        Generate ledger PDF for a party
        
        Args:
            party_code: Party code
            company_id: Company ID
            
        Returns:
            PDF bytes
        """
        logger.info("generating_ledger_pdf", party_code=party_code, company_id=company_id)
        
        try:
            # Generate ledger report
            report = ledger_data_service.generate_ledger_report(party_code, company_id=company_id)
            
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
        schedule_delay: Optional[int] = None,
        party_templates: Optional[Dict[str, str]] = None,
        company_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Send reminders to selected parties with anti-spam measures

        Args:
            party_codes: List of party codes to send to
            template_id: Template ID to use as default
            sent_by: Who triggered the send ("manual" or "scheduler")
            schedule_delay: Delay in seconds before sending (None = immediate)
            party_templates: Per-party template overrides {party_code: template_id}

        Returns:
            Dict with batch_id and session_id
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
            config = self.config_service.get_config(scope_key=company_id)
            template = self.config_service.get_template(template_id, scope_key=company_id) # needs scope update?
            template = next((t for t in config.templates if t.id == template_id), None)
            if template is None:
                raise ValueError(f"Template '{template_id}' not found")

            session = await anti_spam_service.create_session(
                party_codes=party_codes,
                template_id=template_id
            )
            session.metrics.start_time = datetime.now()

            batch = ReminderBatch(
                batch_id=batch_id,
                template_id=template_id,
                party_count=len(party_codes),
                parties=party_codes,
                status=REMINDER_STATUS_SENDING
            )

            startup_delay_mins = anti_spam_service.calculate_startup_delay()
            if startup_delay_mins > 0:
                session.state = SessionState.STARTING
                logger.info(
                    "startup_delay_starting",
                    batch_id=batch_id,
                    session_id=session.session_id,
                    delay_minutes=startup_delay_mins
                )

                provider = BaileysProvider()
                await provider.set_presence(online=True)

                startup_delay_seconds = startup_delay_mins * 60
                await asyncio.sleep(startup_delay_seconds)

                logger.info(
                    "startup_delay_complete",
                    batch_id=batch_id,
                    session_id=session.session_id
                )

            session.state = SessionState.ONLINE

            results = {}
            templates_used: Dict[str, str] = {}

            for i, party_code in enumerate(party_codes):
                try:
                    await session.wait_if_paused()
                    if session.check_stop():
                        logger.info(
                            "session_stopped_by_user",
                            batch_id=batch_id,
                            session_id=session.session_id,
                            processed=i
                        )
                        break

                    session.current_index = i

                    effective_template_id = self._resolve_effective_template(
                        party_code=party_code,
                        batch_template_id=template_id,
                        party_templates=party_templates,
                        company_id=company_id
                    )
                    templates_used[party_code] = effective_template_id

                    effective_template = next((t for t in config.templates if t.id == effective_template_id), None)
                    if effective_template is None:
                        raise ValueError(f"Template '{effective_template_id}' not found")

                    calculation = await self.calculator.calculate_for_party(party_code, company_id=company_id)

                    session.current_index = i

                    if calculation.amount_due <= 0:
                        results[party_code] = {
                            "status": "skipped",
                            "reason": "amount_due_not_positive"
                        }
                        continue

                    pdf_bytes = await self.generate_ledger_pdf(party_code, company_id=company_id)

                    if pdf_inflation_service._enabled:
                        pdf_path = str(self._ledger_dir / f"ledger_{party_code}_{batch_id}.pdf")
                        inflated_path = str(self._ledger_dir / f"ledger_{party_code}_{batch_id}_inflated.pdf")
                        with open(pdf_path, 'wb') as f:
                            f.write(pdf_bytes)
                        pdf_inflation_service.inflate_pdf(
                            pdf_path,
                            inflated_path,
                            party_code=party_code
                        )
                        pdf_path = inflated_path
                    else:
                        pdf_path = str(self._ledger_dir / f"ledger_{party_code}_{batch_id}.pdf")
                        with open(pdf_path, 'wb') as f:
                            f.write(pdf_bytes)

                    party_info = ledger_data_service.get_customer_info(party_code, company_id=company_id)

                    variables = self.template_svc.get_template_variables(
                        party_code=party_code,
                        amount_due=float(calculation.amount_due)
                    )
                    message = self.template_svc.render_template(effective_template, variables)

                    if message_inflation_service._enabled:
                        message = message_inflation_service.inject_invisible_chars(message)

                    if party_info.phone:
                        provider_name = self._resolve_delivery_provider(config.default_provider)
                        media_ref = pdf_path if provider_name == "baileys" else None

                        if media_ref is None:
                            logger.warning(
                                "reminder_media_not_supported_for_provider",
                                provider=provider_name,
                                party_code=party_code,
                            )

                        message_db.enqueue_message(
                            phone=party_info.phone,
                            message=message,
                            pdf_url=media_ref,
                            provider=provider_name,
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

                    if i < len(party_codes) - 1:
                        await asyncio.sleep(config.schedule.delay_between_messages)

                except Exception as ex:
                    logger.error(
                        "reminder_send_failed",
                        party_code=party_code,
                        batch_id=batch_id,
                        error=str(ex)
                    )
                    results[party_code] = {
                        "status": "failed",
                        "error": str(ex)
                    }

            self._persist_template_overrides(templates_used, company_id=company_id)

            batch.status = REMINDER_STATUS_COMPLETED
            batch.results = results
            batch.sent_at = datetime.now()

            session.metrics.end_time = datetime.now()
            session.state = SessionState.COMPLETED

            logger.info(
                "reminders_batch_completed",
                batch_id=batch_id,
                total=len(party_codes),
                successful=sum(1 for r in results.values() if r.get("status") == "queued"),
                failed=sum(1 for r in results.values() if r.get("status") == "failed"),
                session_id=session.session_id,
                duration_seconds=session.metrics.duration_seconds
            )

            if anti_spam_service.get_config().send_session_reports:
                await self._send_session_report(session)

            return {
                "batch_id": batch_id,
                "session_id": session.session_id,
            }

        except Exception as e:
            logger.error(
                "send_reminders_failed",
                batch_id=batch_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def pause_session(self, session_id: str) -> bool:
        """Pause an active reminder session.
        
        Args:
            session_id: Session ID to pause
            
        Returns:
            True if paused successfully
        """
        return await anti_spam_service.pause_session(session_id)
    
    async def resume_session(self, session_id: str) -> bool:
        """Resume a paused reminder session.
        
        Args:
            session_id: Session ID to resume
            
        Returns:
            True if resumed successfully
        """
        return await anti_spam_service.resume_session(session_id)
    
    async def stop_session(self, session_id: str) -> bool:
        """Stop an active reminder session permanently.
        
        Args:
            session_id: Session ID to stop
            
        Returns:
            True if stopped successfully
        """
        return await anti_spam_service.stop_session(session_id)

    def _resolve_effective_template(
        self,
        party_code: str,
        batch_template_id: str,
        party_templates: Optional[Dict[str, str]] = None,
        company_id: str = "default"
    ) -> str:
        """
        Resolve effective template for a party with precedence:
        1. Request-level override (party_templates)
        2. Persisted party config custom_template_id
        3. Batch default template
        """
        if party_templates and party_code in party_templates:
            return party_templates[party_code]

        config = self.config_service.get_config(scope_key=company_id)
        party_config = config.parties.get(party_code)
        if party_config and party_config.custom_template_id:
            return party_config.custom_template_id

        return batch_template_id

    def _persist_template_overrides(self, templates_used: Dict[str, str], company_id: str = "default") -> None:
        """
        Persist template overrides to party configs for parties where
        a non-default template was used in this batch.
        """
        config = self.config_service.get_config(scope_key=company_id)
        changed = False
        
        for party_code, template_id in templates_used.items():
            party_config = config.parties.get(party_code)
            if party_config is None:
                party_config = PartyConfig()

            if party_config.custom_template_id != template_id:
                party_config.custom_template_id = template_id
                config.parties[party_code] = party_config
                changed = True
                
        if changed:
            self.config_service.save_config(config, scope_key=company_id)

    async def get_session_status(self, session_id: str) -> Optional[dict]:
        """Get status of a reminder session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session status dict or None
        """
        return anti_spam_service.get_session_summary(session_id)
    
    async def get_active_sessions(self) -> List[dict]:
        """Get all active reminder sessions.
        
        Returns:
            List of session status dicts
        """
        sessions = anti_spam_service.get_active_sessions()
        summaries = [anti_spam_service.get_session_summary(s.session_id) for s in sessions]
        return [s for s in summaries if s is not None]
    
    async def _send_session_report(self, session: ReminderSession):
        """Send session completion report to admin.
        
        Args:
            session: Completed session
        """
        try:
            config = anti_spam_service.get_config()
            admin_phone = config.admin_phone
            
            if not admin_phone:
                logger.warning("session_report_no_admin_phone", session_id=session.session_id)
                return
            
            # Format report message
            duration_mins = int(session.metrics.duration_seconds / 60)
            duration_secs = int(session.metrics.duration_seconds % 60)
            
            report = f"""📊 Reminder Session Complete
━━━━━━━━━━━━━━━━━━━━━
⏱️ Duration: {duration_mins}m {duration_secs}s
👥 Total: {session.metrics.total_messages} parties
✅ Sent: {session.metrics.sent_count}
❌ Failed: {session.metrics.failed_count}

⏱️ Anti-Spam Metrics:
• Avg delay: {round(session.metrics.avg_delay_seconds, 1)}s
• Typing simulation: {'ON' if config.typing_simulation else 'OFF'}
• Total typing time: {int(session.metrics.typing_time_total)}s
• Total reading time: {int(session.metrics.reading_time_total)}s"""
            
            # Add unsaved contacts info if any
            if session.metrics.unsaved_contacts:
                report += f"""

⚠️ Attention Required:
• {len(session.metrics.unsaved_contacts)} numbers may be unsaved"""
                for contact in session.metrics.unsaved_contacts[:3]:  # Show first 3
                    report += f"\n• {contact.get('name', 'Unknown')}: {contact.get('phone', 'N/A')}"
                if len(session.metrics.unsaved_contacts) > 3:
                    report += f"\n• ... and {len(session.metrics.unsaved_contacts) - 3} more"
                
                report += "\n\n💾 Recommendation: Save these contacts to phone"
            
            # Queue report message to admin
            message_db.enqueue_message(
                phone=admin_phone,
                message=report,
                provider="baileys",
                source="admin_report"
            )
            
            logger.info(
                "session_report_queued",
                session_id=session.session_id,
                admin_phone=admin_phone
            )
            
        except Exception as e:
            logger.error(
                "session_report_failed",
                session_id=session.session_id,
                error=str(e)
            )
    
    async def get_stats(self, company_id: str = "default") -> ReminderStats:
        """Get reminder system statistics"""
        snap = self.snapshot_db.get_status(company_id=company_id)
        page = self.get_eligible_parties_page(
            min_amount_due=Decimal("0.01"),
            include_zero=False,
            filter_by="all",
            offset=0,
            limit=100000,
            company_id=company_id,
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
