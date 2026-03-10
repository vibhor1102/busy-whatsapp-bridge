from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import structlog

from app.config import get_settings
from app.services.baileys_bridge import baileys_bridge
from app.services.dispatch_incident_service import dispatch_incident_service
from app.services.dispatch_policy_service import dispatch_policy_service
from app.services.reminder_config_service import reminder_config_service
from app.services.reminder_service import reminder_service
from app.services.weekly_reminder_planner_service import weekly_reminder_planner_service

logger = structlog.get_logger()


class DispatchEngineService:
    """Unified control path for planner, reminder release, and bridge incidents."""

    def __init__(self) -> None:
        self._last_maintenance: Dict[str, datetime] = {}
        self._maintenance_interval_seconds = 60
        self._lock = asyncio.Lock()

    @staticmethod
    def _today() -> date:
        return date.today()

    @staticmethod
    def _same_day_refresh(refresh_stats: Dict[str, Any]) -> bool:
        stamp = refresh_stats.get("last_refresh_at")
        if not stamp:
            return False
        try:
            refreshed = datetime.fromisoformat(stamp)
        except ValueError:
            return False
        return refreshed.date() == date.today()

    async def sync_bridge_status(self) -> Dict[str, Any]:
        bridge_status = await baileys_bridge.get_status()
        incident = dispatch_incident_service.sync_bridge_status(bridge_status)
        return {
            "bridge_status": bridge_status,
            "incident": incident,
            "dispatch_blocked": dispatch_incident_service.is_dispatch_blocked(),
        }

    async def _build_recipient_inputs(self, company_id: str) -> List[Dict[str, Any]]:
        parties = await reminder_service.get_eligible_parties(
            limit=5000,
            company_id=company_id,
        )
        return [
            {
                "party_code": party.code,
                "recipient_name": party.name,
                "phone": party.phone,
                "amount_due": float(party.amount_due),
            }
            for party in parties
            if party.permanent_enabled and float(party.amount_due) > 0
        ]

    async def ensure_current_plan(
        self,
        company_id: str,
        *,
        force_replan: bool = False,
        reason: str = "maintenance",
    ) -> Optional[Dict[str, Any]]:
        refresh_stats = reminder_config_service.get_refresh_stats(scope_key=company_id)
        if not self._same_day_refresh(refresh_stats):
            return None

        current_plan = weekly_reminder_planner_service.get_current_plan(company_id)
        refresh_stamp = refresh_stats.get("last_refresh_at")
        if (
            not force_replan
            and current_plan
            and current_plan.get("snapshot_date") == refresh_stamp
            and not current_plan.get("invalidated_at")
        ):
            return current_plan

        recipients = await self._build_recipient_inputs(company_id)
        plan = weekly_reminder_planner_service.upsert_plan(
            company_id=company_id,
            recipients=recipients,
            snapshot_date=refresh_stamp,
            reason=reason,
        )
        logger.info(
            "dispatch_plan_upserted",
            company_id=company_id,
            recipient_count=len(recipients),
            reason=reason,
        )
        return plan

    async def release_due_reminders(
        self,
        company_id: str,
        *,
        force_replan: bool = False,
        sent_by: str = "planner",
    ) -> Dict[str, Any]:
        bridge_context = await self.sync_bridge_status()
        incident_status = dispatch_incident_service.get_status()
        refresh_stats = reminder_config_service.get_refresh_stats(scope_key=company_id)
        same_day_snapshot = self._same_day_refresh(refresh_stats)
        policy_allowed, policy_reason = dispatch_policy_service.can_dispatch_non_transactional(company_id)

        if bridge_context["dispatch_blocked"]:
            return {
                "status": "held_incident",
                "reason": "dispatch_incident",
                "incident": incident_status.get("incident"),
            }

        if not same_day_snapshot:
            return {
                "status": "awaiting_snapshot",
                "reason": "same_day_snapshot_required",
            }

        if not policy_allowed:
            return {
                "status": "held_policy",
                "reason": policy_reason,
            }

        plan = await self.ensure_current_plan(
            company_id,
            force_replan=force_replan,
            reason="forced_replan" if force_replan else "release_due",
        )
        if not plan:
            return {
                "status": "awaiting_snapshot",
                "reason": "same_day_snapshot_required",
            }

        due_party_codes = weekly_reminder_planner_service.get_due_party_codes(company_id)
        if not due_party_codes:
            return {
                "status": "idle",
                "reason": "nothing_due",
                "week_key": plan.get("week_key"),
            }

        template = reminder_config_service.get_active_template(scope_key=company_id)
        result = await reminder_service.send_reminders_to_parties(
            party_codes=due_party_codes,
            template_id=template.id,
            sent_by=sent_by,
            company_id=company_id,
        )

        batch_id = result["batch_id"]
        weekly_reminder_planner_service.mark_released(
            company_id=company_id,
            party_codes=due_party_codes,
            batch_id=batch_id,
        )
        reminder_config_service.record_reminder_sent(scope_key=company_id)

        return {
            "status": "released",
            "batch_id": batch_id,
            "session_id": result.get("session_id"),
            "party_codes": due_party_codes,
            "count": len(due_party_codes),
        }

    async def run_periodic_maintenance(self) -> Dict[str, Any]:
        async with self._lock:
            settings = get_settings()
            now = datetime.now()
            results: Dict[str, Any] = {}

            await self.sync_bridge_status()

            for company_id in settings.database.companies.keys():
                last_run = self._last_maintenance.get(company_id)
                if last_run and (now - last_run).total_seconds() < self._maintenance_interval_seconds:
                    continue

                try:
                    plan = await self.ensure_current_plan(company_id, reason="worker_maintenance")
                    release_result = await self.release_due_reminders(company_id)
                    results[company_id] = {
                        "plan_week_key": plan.get("week_key") if plan else None,
                        "release": release_result,
                    }
                except Exception as exc:
                    logger.error(
                        "dispatch_maintenance_failed",
                        company_id=company_id,
                        error=str(exc),
                        exc_info=True,
                    )
                    results[company_id] = {"status": "error", "error": str(exc)}
                finally:
                    self._last_maintenance[company_id] = now

            return results

    async def get_operations_status(self, company_id: str) -> Dict[str, Any]:
        bridge_status = await baileys_bridge.get_status()
        dispatch_incident_service.sync_bridge_status(bridge_status)
        incident_status = dispatch_incident_service.get_status()
        refresh_stats = reminder_config_service.get_refresh_stats(scope_key=company_id)
        plan_summary = weekly_reminder_planner_service.summarize_plan(company_id)
        current_plan = weekly_reminder_planner_service.get_current_plan(company_id)
        due_party_codes = weekly_reminder_planner_service.get_due_party_codes(company_id)
        policy = dispatch_policy_service.get_policy(company_id)
        policy_allowed, policy_reason = dispatch_policy_service.can_dispatch_non_transactional(company_id)

        return {
            "company_id": company_id,
            "bridge": bridge_status,
            "incident": incident_status,
            "dispatch_mode": dispatch_policy_service.get_dispatch_mode(company_id),
            "policy": {
                **policy.model_dump(),
                "can_dispatch_reminders": policy_allowed and not dispatch_incident_service.is_dispatch_blocked(),
                "blocked_reason": policy_reason,
            },
            "snapshot": {
                **refresh_stats,
                "same_day_ready": self._same_day_refresh(refresh_stats),
            },
            "planner": {
                "current_plan": current_plan,
                "summary": plan_summary,
                "due_today": due_party_codes,
            },
        }


dispatch_engine_service = DispatchEngineService()
