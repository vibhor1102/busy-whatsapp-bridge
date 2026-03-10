import asyncio
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from app.database.message_queue import MessageQueueDB
from app.services.dispatch_engine_service import dispatch_engine_service
from app.services.weekly_reminder_planner_service import WeeklyReminderPlannerService


def test_defer_message_preserves_retry_count(tmp_path):
    db = MessageQueueDB(db_path=str(tmp_path / "messages.db"))
    queue_id = db.enqueue_message(
        phone="+919999999999",
        message="hold me",
        provider="baileys",
        source="payment_reminder",
    )

    db.defer_message(queue_id, delay_seconds=180, reason="dispatch_blocked:incident_active")

    message = db.get_message_by_id(queue_id)
    assert message is not None
    assert message["status"] == "retrying"
    assert message["retry_count"] == 0
    assert "dispatch_blocked" in str(message["error_message"])


def test_weekly_planner_uses_weekend_as_catchup(monkeypatch):
    planner = WeeklyReminderPlannerService()
    planner._state = {"companies": {}}

    fake_config = SimpleNamespace(schedule=SimpleNamespace(delay_between_messages=300))
    monkeypatch.setattr(
        "app.services.weekly_reminder_planner_service.reminder_config_service.get_config",
        lambda scope_key: fake_config,
    )

    recipients = [
        {"party_code": f"P{i}", "recipient_name": f"Party {i}", "phone": f"+9199999999{i:02d}", "amount_due": 1000 - i}
        for i in range(1, 71)
    ]

    plan = planner.upsert_plan(
        company_id="database_1",
        recipients=recipients,
        snapshot_date=datetime.now().isoformat(),
        reason="test",
        today=date(2026, 3, 13),  # Friday
    )

    saturday_entries = [entry for entry in plan["entries"] if entry.get("planned_for") == "2026-03-14"]
    sunday_entries = [entry for entry in plan["entries"] if entry.get("planned_for") == "2026-03-15"]

    assert saturday_entries or sunday_entries


def test_release_due_reminders_requires_same_day_snapshot(monkeypatch):
    async def fake_bridge_status():
        return {"state": "connected", "sessionState": "healthy"}

    monkeypatch.setattr("app.services.dispatch_engine_service.baileys_bridge.get_status", fake_bridge_status)
    monkeypatch.setattr("app.services.dispatch_engine_service.dispatch_incident_service.sync_bridge_status", lambda status: None)
    monkeypatch.setattr("app.services.dispatch_engine_service.dispatch_incident_service.get_status", lambda: {"incident": None})
    monkeypatch.setattr("app.services.dispatch_engine_service.dispatch_incident_service.is_dispatch_blocked", lambda: False)
    monkeypatch.setattr(
        "app.services.dispatch_engine_service.reminder_config_service.get_refresh_stats",
        lambda scope_key: {"last_refresh_at": (datetime.now() - timedelta(days=1)).isoformat()},
    )

    result = asyncio.run(dispatch_engine_service.release_due_reminders("database_1"))

    assert result["status"] == "awaiting_snapshot"
