from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import structlog

from app.config import get_roaming_appdata_path
from app.models.reminder_schemas import DispatchPolicyConfig
from app.services.reminder_config_service import reminder_config_service

logger = structlog.get_logger()


class DispatchPolicyService:
    """Central control plane for supervised dispatch behavior."""

    def __init__(self) -> None:
        self._state_path = get_roaming_appdata_path() / "data" / "dispatch_state.json"
        self._lock = Lock()
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self._state_path.exists():
            try:
                with open(self._state_path, "r", encoding="utf-8") as handle:
                    return json.load(handle)
            except Exception as exc:
                logger.warning("dispatch_state_load_failed", error=str(exc))
        return {"pending_batches": {}}

    def _save_state(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._state_path, "w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2)

    def get_policy(self, company_id: str) -> DispatchPolicyConfig:
        return reminder_config_service.get_config(scope_key=company_id).dispatch_policy

    def update_policy(self, company_id: str, policy_data: Dict[str, Any]) -> DispatchPolicyConfig:
        config = reminder_config_service.get_config(scope_key=company_id)
        merged = config.dispatch_policy.model_dump()
        merged.update(policy_data)
        config.dispatch_policy = DispatchPolicyConfig(**merged)
        reminder_config_service.save_config(config, scope_key=company_id)
        return config.dispatch_policy

    def get_dispatch_mode(self, company_id: str) -> str:
        policy = self.get_policy(company_id)
        if policy.paused:
            return "paused"
        if policy.require_batch_approval:
            return "supervised_batch"
        return "automatic_invoice"

    def is_within_business_hours(self, company_id: str, when: Optional[datetime] = None) -> bool:
        policy = self.get_policy(company_id)
        if not policy.business_hours_enabled:
            return True
        current = when or datetime.now(ZoneInfo(policy.timezone))
        if current.tzinfo is None:
            current = current.replace(tzinfo=ZoneInfo(policy.timezone))
        start = datetime.strptime(policy.business_hours_start, "%H:%M").time()
        end = datetime.strptime(policy.business_hours_end, "%H:%M").time()
        now_time = current.timetz().replace(tzinfo=None)
        if start <= end:
            return start <= now_time <= end
        return now_time >= start or now_time <= end

    def can_dispatch_non_transactional(self, company_id: str) -> tuple[bool, Optional[str]]:
        policy = self.get_policy(company_id)
        if policy.paused:
            return False, "dispatch_paused"
        if not self.is_within_business_hours(company_id):
            return False, "outside_business_hours"
        return True, None

    def register_pending_batch(self, *, company_id: str, batch_id: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            pending = {
                "batch_id": batch_id,
                "session_id": session_id,
                "company_id": company_id,
                "status": "pending_approval",
                "created_at": datetime.now().isoformat(),
                "payload": payload,
            }
            self._state.setdefault("pending_batches", {})[batch_id] = pending
            self._save_state()
            return pending

    def approve_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            batch = self._state.get("pending_batches", {}).get(batch_id)
            if not batch:
                return None
            batch["status"] = "approved"
            batch["approved_at"] = datetime.now().isoformat()
            self._save_state()
            return batch

    def reject_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            batch = self._state.get("pending_batches", {}).get(batch_id)
            if not batch:
                return None
            batch["status"] = "rejected"
            batch["rejected_at"] = datetime.now().isoformat()
            self._save_state()
            return batch

    def get_pending_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        return self._state.get("pending_batches", {}).get(batch_id)

    def list_pending_batches(self, company_id: Optional[str] = None) -> List[Dict[str, Any]]:
        items = list(self._state.get("pending_batches", {}).values())
        if company_id:
            items = [item for item in items if item.get("company_id") == company_id]
        return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


dispatch_policy_service = DispatchPolicyService()
