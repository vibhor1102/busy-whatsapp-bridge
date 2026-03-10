from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

import structlog

from app.config import get_roaming_appdata_path

logger = structlog.get_logger()


class DispatchIncidentService:
    """Persist and classify dispatch-impacting Baileys incidents."""

    def __init__(self) -> None:
        self._path = get_roaming_appdata_path() / "data" / "dispatch_incident_state.json"
        self._lock = Lock()
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, dict):
                        return data
            except Exception as exc:
                logger.warning("dispatch_incident_state_load_failed", error=str(exc))
        return {"active_incident": None, "last_bridge_status": None, "last_updated": None}

    def _save_state(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2)

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat()

    def get_active_incident(self) -> Optional[Dict[str, Any]]:
        return self._state.get("active_incident")

    def get_last_bridge_status(self) -> Optional[Dict[str, Any]]:
        return self._state.get("last_bridge_status")

    def _make_incident(
        self,
        *,
        kind: str,
        title: str,
        message: str,
        severity: str,
        bridge_status: Dict[str, Any],
        requires_manual_resolution: bool,
    ) -> Dict[str, Any]:
        current = self.get_active_incident()
        created_at = current["created_at"] if current and current.get("kind") == kind else self._now()
        return {
            "kind": kind,
            "title": title,
            "message": message,
            "severity": severity,
            "created_at": created_at,
            "updated_at": self._now(),
            "acknowledged_at": current.get("acknowledged_at") if current else None,
            "ignored_at": current.get("ignored_at") if current else None,
            "resolved_at": None,
            "requires_manual_resolution": requires_manual_resolution,
            "blocked": True,
            "recovery_ready": False,
            "bridge_state": bridge_status.get("state"),
            "session_state": bridge_status.get("sessionState"),
            "bridge_status": bridge_status,
        }

    def _classify_bridge_status(self, bridge_status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        state = (bridge_status.get("state") or "").strip().lower()
        session_state = (bridge_status.get("sessionState") or "").strip().lower()
        reason = (bridge_status.get("lastDisconnectReason") or "").strip()

        if state == "logged_out":
            return self._make_incident(
                kind="logout_restriction",
                title="WhatsApp session logged out",
                message=reason or "The linked WhatsApp session logged out and requires guided recovery.",
                severity="critical",
                bridge_status=bridge_status,
                requires_manual_resolution=True,
            )

        if bridge_status.get("isDegraded") or session_state == "degraded":
            return self._make_incident(
                kind="session_degraded",
                title="WhatsApp session degraded",
                message="Baileys session health is degraded. Dispatch is held until recovery completes.",
                severity="high",
                bridge_status=bridge_status,
                requires_manual_resolution=False,
            )

        if state in {"unreachable", "disconnected"}:
            return self._make_incident(
                kind="bridge_unavailable",
                title="Baileys bridge unavailable",
                message=reason or "The Baileys bridge is unreachable or disconnected.",
                severity="high",
                bridge_status=bridge_status,
                requires_manual_resolution=True,
            )

        if state in {"connecting", "reconnecting"}:
            return self._make_incident(
                kind="bridge_reconnecting",
                title="Baileys is reconnecting",
                message="The bridge is reconnecting. Outbound traffic is paused until health returns.",
                severity="medium",
                bridge_status=bridge_status,
                requires_manual_resolution=False,
            )

        return None

    def sync_bridge_status(self, bridge_status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._state["last_bridge_status"] = bridge_status
            self._state["last_updated"] = self._now()

            classified = self._classify_bridge_status(bridge_status)
            current = self._state.get("active_incident")

            if classified:
                if current and current.get("kind") == classified["kind"]:
                    classified["acknowledged_at"] = current.get("acknowledged_at")
                    classified["ignored_at"] = current.get("ignored_at")
                self._state["active_incident"] = classified
                self._save_state()
                return classified

            if current:
                if current.get("requires_manual_resolution"):
                    current["recovery_ready"] = True
                    current["updated_at"] = self._now()
                    current["bridge_status"] = bridge_status
                    current["bridge_state"] = bridge_status.get("state")
                    current["session_state"] = bridge_status.get("sessionState")
                    self._state["active_incident"] = current
                else:
                    current["resolved_at"] = self._now()
                    current["blocked"] = False
                    self._state["active_incident"] = None
                self._save_state()

            return self._state.get("active_incident")

    def acknowledge_incident(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            current = self._state.get("active_incident")
            if not current:
                return None
            current["acknowledged_at"] = self._now()
            current["updated_at"] = self._now()
            self._state["active_incident"] = current
            self._save_state()
            return current

    def ignore_incident(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            current = self._state.get("active_incident")
            if not current:
                return None
            current["ignored_at"] = self._now()
            current["acknowledged_at"] = current.get("acknowledged_at") or current["ignored_at"]
            current["updated_at"] = self._now()
            self._state["active_incident"] = current
            self._save_state()
            return current

    def resolve_incident(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            current = self._state.get("active_incident")
            if not current:
                return None
            current["resolved_at"] = self._now()
            current["blocked"] = False
            current["updated_at"] = self._now()
            self._state["active_incident"] = None
            self._save_state()
            return current

    def is_dispatch_blocked(self) -> bool:
        current = self._state.get("active_incident")
        return bool(current and current.get("blocked"))

    def get_attention_required(self) -> bool:
        current = self._state.get("active_incident")
        if not current:
            return False
        return not current.get("acknowledged_at") and not current.get("ignored_at")

    def get_status(self) -> Dict[str, Any]:
        return {
            "incident": self._state.get("active_incident"),
            "attention_required": self.get_attention_required(),
            "dispatch_blocked": self.is_dispatch_blocked(),
            "last_bridge_status": self._state.get("last_bridge_status"),
            "last_updated": self._state.get("last_updated"),
        }


dispatch_incident_service = DispatchIncidentService()
