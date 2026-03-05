import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api import reminder_routes
from app.models.reminder_schemas import CreateBatchRequest, PartyConfig
from app.services.reminder_service import ReminderService


class DummyConfigService:
    def __init__(self, configs):
        self.configs = configs
        self.save_calls = []

    def get_config(self, scope_key=None):
        return self.configs[scope_key or "default"]

    def save_config(self, config, scope_key=None):
        self.save_calls.append(scope_key or "default")
        self.configs[scope_key or "default"] = config


class DummySnapshotDB:
    def __init__(self, eligible_by_company):
        self.eligible_by_company = eligible_by_company
        self.bulk_calls = []

    def get_positive_due_party_codes(self, company_id="default"):
        return list(self.eligible_by_company.get(company_id, []))

    def set_permanent_enabled_for_positive_due(self, selected_codes, company_id="default"):
        self.bulk_calls.append((company_id, set(selected_codes)))


def _build_service(config_service, snapshot_db):
    service = object.__new__(ReminderService)
    service.config_service = config_service
    service.snapshot_db = snapshot_db
    return service


def test_selection_persistence_updates_only_current_eligible_universe():
    config = SimpleNamespace(parties={"999": PartyConfig(enabled=True)})
    config_service = DummyConfigService({"company_a": config})
    snapshot_db = DummySnapshotDB({"company_a": ["101", "102"]})
    service = _build_service(config_service, snapshot_db)

    service.persist_selection_preferences_on_send_start(
        selected_party_codes=["101"],
        company_id="company_a",
    )

    assert config.parties["101"].enabled is True
    assert config.parties["102"].enabled is False
    assert config.parties["999"].enabled is True
    assert snapshot_db.bulk_calls == [("company_a", {"101"})]


def test_selection_persistence_is_company_scoped():
    config_a = SimpleNamespace(parties={})
    config_b = SimpleNamespace(parties={"201": PartyConfig(enabled=True)})
    config_service = DummyConfigService({"company_a": config_a, "company_b": config_b})
    snapshot_db = DummySnapshotDB({"company_a": ["101"], "company_b": ["201"]})
    service = _build_service(config_service, snapshot_db)

    service.persist_selection_preferences_on_send_start(
        selected_party_codes=["101"],
        company_id="company_a",
    )

    assert config_a.parties["101"].enabled is True
    assert config_b.parties["201"].enabled is True
    assert snapshot_db.bulk_calls == [("company_a", {"101"})]


def test_explicit_template_override_persistence_only_updates_explicit_map():
    config = SimpleNamespace(
        parties={
            "101": PartyConfig(custom_template_id="old"),
            "102": PartyConfig(custom_template_id="legacy"),
        }
    )
    config_service = DummyConfigService({"company_a": config})
    snapshot_db = DummySnapshotDB({"company_a": []})
    service = _build_service(config_service, snapshot_db)

    service.persist_explicit_template_overrides(
        explicit_overrides={"101": "urgent", "102": "", "103": "first"},
        company_id="company_a",
    )

    assert config.parties["101"].custom_template_id == "urgent"
    assert config.parties["102"].custom_template_id is None
    assert config.parties["103"].custom_template_id == "first"


def test_batch_route_stale_data_does_not_persist(monkeypatch):
    stale = (datetime.now() - timedelta(hours=3)).isoformat()
    monkeypatch.setattr(
        reminder_routes.reminder_config_service,
        "get_refresh_stats",
        lambda scope_key=None: {"last_refresh_at": stale, "last_reminder_sent_at": None},
    )

    called = {"selection": False}
    monkeypatch.setattr(
        reminder_routes.reminder_service,
        "persist_selection_preferences_on_send_start",
        lambda *args, **kwargs: called.__setitem__("selection", True),
    )

    req = CreateBatchRequest(party_codes=["101"], template_id="standard")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(reminder_routes.send_reminders_batch(req, BackgroundTasks(), "company_a"))

    assert exc.value.status_code == 409
    assert called["selection"] is False


def test_batch_route_success_persists_before_background(monkeypatch):
    fresh = datetime.now().isoformat()
    monkeypatch.setattr(
        reminder_routes.reminder_config_service,
        "get_refresh_stats",
        lambda scope_key=None: {"last_refresh_at": fresh, "last_reminder_sent_at": None},
    )

    anti_spam_cfg = SimpleNamespace(
        enabled=False,
        reminder_cooldown_enabled=False,
        reminder_cooldown_minutes=60,
    )
    monkeypatch.setattr(reminder_routes.anti_spam_service, "get_config", lambda: anti_spam_cfg)

    async def _fake_create_session(*args, **kwargs):
        return SimpleNamespace(session_id="session-1")

    monkeypatch.setattr(reminder_routes.anti_spam_service, "create_session", _fake_create_session)

    called = {"selection": False, "templates": False}
    monkeypatch.setattr(
        reminder_routes.reminder_service,
        "persist_selection_preferences_on_send_start",
        lambda *args, **kwargs: called.__setitem__("selection", True),
    )
    monkeypatch.setattr(
        reminder_routes.reminder_service,
        "persist_explicit_template_overrides",
        lambda *args, **kwargs: called.__setitem__("templates", True),
    )

    async def _fake_send(*args, **kwargs):
        return None

    monkeypatch.setattr(reminder_routes.reminder_service, "send_reminders_to_parties", _fake_send)

    req = CreateBatchRequest(
        party_codes=["101"],
        template_id="standard",
        party_templates={"101": "urgent"},
    )
    resp = asyncio.run(reminder_routes.send_reminders_batch(req, BackgroundTasks(), "company_a"))

    assert resp["status"] == "success"
    assert resp["session_id"] == "session-1"
    assert called["selection"] is True
    assert called["templates"] is True
