import asyncio
from pathlib import Path

from app.config import Settings, get_settings
from app.main import ConfigUpdateRequest, update_config_file
from app.services.reminder_config_service import ReminderConfigService


def _seed_minimal_conf(tmp_path):
    config_dir = Path(tmp_path) / "BusyWhatsappBridge"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "conf.json").write_text("{}", encoding="utf-8")


def test_default_config_uses_three_starter_templates(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _seed_minimal_conf(tmp_path)
    get_settings.cache_clear()

    service = ReminderConfigService()
    config = service._create_default_config()

    template_ids = [t.id for t in config.templates]
    assert template_ids == ["standard", "polite", "firm"]
    assert config.active_template_id == "standard"
    assert "😊" in config.templates[1].content
    assert "⚠️" in config.templates[2].content


def test_ensure_scope_initialized_keeps_existing_company_templates(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _seed_minimal_conf(tmp_path)
    get_settings.cache_clear()

    service = ReminderConfigService()
    scope = "company_a"

    custom_config = service._create_default_config()
    custom_config.templates = [custom_config.templates[0]]
    custom_config.templates[0].name = "Custom Template"
    config_path = service._get_config_path(scope)
    service._save_config_to_file(custom_config, config_path)

    service.ensure_scope_initialized(scope)
    loaded = service.reload_config(scope)

    assert len(loaded.templates) == 1
    assert loaded.templates[0].name == "Custom Template"


def test_settings_update_bootstraps_only_new_company_scopes(monkeypatch):
    base_settings = Settings.model_validate(
        {
            "database": {
                "companies": {
                    "company_old": {"bds_file_path": r"C:\data\old.bds", "bds_password": "x"}
                }
            }
        }
    )

    saved_payload = {}
    initialized_scopes = []

    monkeypatch.setattr("app.main.load_settings", lambda: base_settings)
    monkeypatch.setattr("app.main.save_settings", lambda settings: saved_payload.setdefault("settings", settings))
    monkeypatch.setattr("app.main.get_settings", get_settings)
    monkeypatch.setattr("app.main.db.refresh_settings", lambda: None)
    monkeypatch.setattr(
        "app.main.reminder_config_service.ensure_scope_initialized",
        lambda company_id: initialized_scopes.append(company_id),
    )

    request = ConfigUpdateRequest(
        companies={
            "company_old": {"bds_file_path": r"C:\data\old.bds", "bds_password": "x"},
            "company_new": {"bds_file_path": r"C:\data\new.bds", "bds_password": "y"},
        }
    )

    result = asyncio.run(update_config_file(request))

    assert result["success"] is True
    assert initialized_scopes == ["company_new"]
    assert "settings" in saved_payload
    assert saved_payload["settings"].database.companies["company_new"]["bds_file_path"].endswith("new.bds")
