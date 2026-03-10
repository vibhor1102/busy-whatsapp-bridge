from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import structlog

from app.config import get_roaming_appdata_path
from app.services.reminder_config_service import reminder_config_service

logger = structlog.get_logger()


class WeeklyReminderPlannerService:
    """Persisted weekly planner for reminder distribution."""

    def __init__(self) -> None:
        self._path = get_roaming_appdata_path() / "data" / "weekly_reminder_plans.json"
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
                logger.warning("weekly_planner_state_load_failed", error=str(exc))
        return {"companies": {}}

    def _save_state(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2)

    @staticmethod
    def _monday_for(day: date) -> date:
        return day - timedelta(days=day.weekday())

    @classmethod
    def current_week_key(cls, day: Optional[date] = None) -> str:
        anchor = cls._monday_for(day or date.today())
        return anchor.isoformat()

    @staticmethod
    def _iso(day: date) -> str:
        return day.isoformat()

    def _company_bucket(self, company_id: str) -> Dict[str, Any]:
        companies = self._state.setdefault("companies", {})
        return companies.setdefault(company_id, {"weeks": {}})

    def get_current_plan(self, company_id: str, day: Optional[date] = None) -> Optional[Dict[str, Any]]:
        week_key = self.current_week_key(day)
        return self._company_bucket(company_id).setdefault("weeks", {}).get(week_key)

    def invalidate_current_plan(self, company_id: str, reason: str) -> None:
        with self._lock:
            plan = self.get_current_plan(company_id)
            if not plan:
                return
            plan["invalidated_at"] = datetime.now().isoformat()
            plan["invalidated_reason"] = reason
            plan["updated_at"] = datetime.now().isoformat()
            self._save_state()

    def _capacity_settings(self, company_id: str, total_enabled: int) -> Dict[str, int]:
        config = reminder_config_service.get_config(scope_key=company_id)
        expected_uptime_hours = 10
        delay_seconds = max(5, int(config.schedule.delay_between_messages or 5))
        estimated_send_seconds = max(75, delay_seconds * 12)
        runtime_capacity = max(25, int((expected_uptime_hours * 3600) / estimated_send_seconds))
        regular_load = max(1, math.ceil(total_enabled / 5)) if total_enabled else 1
        weekday_limit = max(regular_load, min(runtime_capacity, regular_load * 2))
        weekend_limit = weekday_limit
        return {
            "expected_uptime_hours": expected_uptime_hours,
            "runtime_capacity": runtime_capacity,
            "regular_load": regular_load,
            "weekday_limit": weekday_limit,
            "weekend_limit": weekend_limit,
        }

    @staticmethod
    def _remaining_days(today: date) -> Dict[str, List[date]]:
        monday = today - timedelta(days=today.weekday())
        weekdays: List[date] = []
        weekend: List[date] = []
        for offset in range(7):
            current = monday + timedelta(days=offset)
            if current < today:
                continue
            if current.weekday() < 5:
                weekdays.append(current)
            else:
                weekend.append(current)
        return {"weekdays": weekdays, "weekend": weekend}

    @staticmethod
    def _distribute_evenly(items: List[Dict[str, Any]], days: List[date], day_limit: int) -> Dict[str, List[Dict[str, Any]]]:
        allocations = {day.isoformat(): [] for day in days}
        remaining = list(items)
        for index, day in enumerate(days):
            if not remaining:
                break
            days_left = len(days) - index
            target = min(day_limit, math.ceil(len(remaining) / days_left))
            allocations[day.isoformat()] = remaining[:target]
            remaining = remaining[target:]
        if remaining:
            # Append any tiny rounding residue to the last day if there is still room.
            last_key = days[-1].isoformat()
            allocations[last_key].extend(remaining)
        return allocations

    def _build_entries(
        self,
        *,
        company_id: str,
        today: date,
        recipients: List[Dict[str, Any]],
        previous_plan: Optional[Dict[str, Any]],
        snapshot_date: str,
        reason: str,
    ) -> Dict[str, Any]:
        previous_entries = {
            entry["party_code"]: entry
            for entry in (previous_plan or {}).get("entries", [])
        }
        released_codes = {
            code for code, entry in previous_entries.items()
            if entry.get("state") in {"released", "completed"}
        }

        current_candidates = [
            {
                "party_code": item["party_code"],
                "recipient_name": item.get("recipient_name"),
                "phone": item.get("phone"),
                "amount_due": float(item.get("amount_due") or 0),
            }
            for item in recipients
        ]
        current_candidates.sort(key=lambda item: item["amount_due"], reverse=True)

        remaining_days = self._remaining_days(today)
        capacities = self._capacity_settings(company_id, len(current_candidates))

        unscheduled = [item for item in current_candidates if item["party_code"] not in released_codes]
        weekday_days = remaining_days["weekdays"]
        weekend_days = remaining_days["weekend"]
        weekday_limit = capacities["weekday_limit"]
        weekend_limit = capacities["weekend_limit"]

        day_allocations: Dict[str, List[Dict[str, Any]]] = {self._iso(day): [] for day in weekday_days + weekend_days}
        forfeited: List[Dict[str, Any]] = []
        if unscheduled and weekday_days:
            max_weekday_total = weekday_limit * len(weekday_days)
            if len(unscheduled) <= max_weekday_total:
                day_allocations.update(self._distribute_evenly(unscheduled, weekday_days, weekday_limit))
            else:
                primary_slice = unscheduled[:max_weekday_total]
                overflow = unscheduled[max_weekday_total:]
                day_allocations.update(self._distribute_evenly(primary_slice, weekday_days, weekday_limit))
                if weekend_days:
                    saturday = weekend_days[0:1]
                    sunday = weekend_days[1:2]
                    saturday_slice = overflow[:weekend_limit]
                    overflow = overflow[weekend_limit:]
                    if saturday:
                        day_allocations.update(self._distribute_evenly(saturday_slice, saturday, weekend_limit))
                    sunday_slice = overflow[:weekend_limit]
                    overflow = overflow[weekend_limit:]
                    if sunday:
                        day_allocations.update(self._distribute_evenly(sunday_slice, sunday, weekend_limit))
                forfeited = overflow
        elif unscheduled:
            # No remaining weekdays in this week: weekend only or forfeit.
            overflow = list(unscheduled)
            if weekend_days:
                saturday = weekend_days[0:1]
                sunday = weekend_days[1:2]
                saturday_slice = overflow[:weekend_limit]
                overflow = overflow[weekend_limit:]
                if saturday:
                    day_allocations.update(self._distribute_evenly(saturday_slice, saturday, weekend_limit))
                sunday_slice = overflow[:weekend_limit]
                overflow = overflow[weekend_limit:]
                if sunday:
                    day_allocations.update(self._distribute_evenly(sunday_slice, sunday, weekend_limit))
            forfeited = overflow

        entries: List[Dict[str, Any]] = []
        for item in current_candidates:
            previous = previous_entries.get(item["party_code"])
            if previous and previous.get("state") in {"released", "completed"}:
                entries.append(previous)
                continue

            planned_for = None
            state = "planned"
            for day_key, allocated in day_allocations.items():
                match = next((candidate for candidate in allocated if candidate["party_code"] == item["party_code"]), None)
                if match:
                    planned_for = day_key
                    break
            if any(candidate["party_code"] == item["party_code"] for candidate in forfeited):
                state = "forfeited"

            entries.append(
                {
                    "party_code": item["party_code"],
                    "recipient_name": item.get("recipient_name"),
                    "phone": item.get("phone"),
                    "amount_due": item["amount_due"],
                    "planned_for": planned_for,
                    "state": state,
                    "released_at": None,
                    "batch_id": None,
                    "updated_at": datetime.now().isoformat(),
                }
            )

        return {
            "company_id": company_id,
            "week_key": self.current_week_key(today),
            "snapshot_date": snapshot_date,
            "reason": reason,
            "created_at": (previous_plan or {}).get("created_at") or datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "capacities": capacities,
            "entries": entries,
        }

    def upsert_plan(
        self,
        *,
        company_id: str,
        recipients: List[Dict[str, Any]],
        snapshot_date: str,
        reason: str,
        today: Optional[date] = None,
    ) -> Dict[str, Any]:
        anchor = today or date.today()
        week_key = self.current_week_key(anchor)
        with self._lock:
            previous_plan = self._company_bucket(company_id).setdefault("weeks", {}).get(week_key)
            plan = self._build_entries(
                company_id=company_id,
                today=anchor,
                recipients=recipients,
                previous_plan=previous_plan,
                snapshot_date=snapshot_date,
                reason=reason,
            )
            self._company_bucket(company_id)["weeks"][week_key] = plan
            self._save_state()
            return plan

    def mark_released(
        self,
        *,
        company_id: str,
        party_codes: List[str],
        batch_id: str,
        released_at: Optional[str] = None,
        today: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        week_key = self.current_week_key(today)
        with self._lock:
            plan = self._company_bucket(company_id).setdefault("weeks", {}).get(week_key)
            if not plan:
                return None
            released_stamp = released_at or datetime.now().isoformat()
            code_set = set(party_codes)
            for entry in plan.get("entries", []):
                if entry["party_code"] in code_set:
                    entry["state"] = "released"
                    entry["released_at"] = released_stamp
                    entry["batch_id"] = batch_id
                    entry["updated_at"] = released_stamp
            plan["updated_at"] = released_stamp
            self._save_state()
            return plan

    def get_due_party_codes(self, company_id: str, today: Optional[date] = None) -> List[str]:
        plan = self.get_current_plan(company_id, today)
        if not plan:
            return []
        cutoff = (today or date.today()).isoformat()
        due_codes = []
        for entry in plan.get("entries", []):
            planned_for = entry.get("planned_for")
            if not planned_for or entry.get("state") != "planned":
                continue
            if planned_for <= cutoff:
                due_codes.append(entry["party_code"])
        return due_codes

    def summarize_plan(self, company_id: str, today: Optional[date] = None) -> Dict[str, Any]:
        plan = self.get_current_plan(company_id, today)
        if not plan:
            return {"week_key": self.current_week_key(today), "days": [], "totals": {"planned": 0, "released": 0, "forfeited": 0}}

        day_rows: Dict[str, Dict[str, Any]] = {}
        totals = {"planned": 0, "released": 0, "forfeited": 0}
        for entry in plan.get("entries", []):
            planned_for = entry.get("planned_for") or "unassigned"
            row = day_rows.setdefault(
                planned_for,
                {"day": planned_for, "planned_count": 0, "released_count": 0, "forfeited_count": 0, "party_codes": []},
            )
            row["party_codes"].append(entry["party_code"])
            if entry.get("state") == "released":
                row["released_count"] += 1
                totals["released"] += 1
            elif entry.get("state") == "forfeited":
                row["forfeited_count"] += 1
                totals["forfeited"] += 1
            else:
                row["planned_count"] += 1
                totals["planned"] += 1

        return {
            "week_key": plan["week_key"],
            "snapshot_date": plan.get("snapshot_date"),
            "reason": plan.get("reason"),
            "updated_at": plan.get("updated_at"),
            "capacities": plan.get("capacities", {}),
            "days": [day_rows[key] for key in sorted(day_rows.keys())],
            "totals": totals,
        }


weekly_reminder_planner_service = WeeklyReminderPlannerService()
