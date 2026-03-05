from fastapi import HTTPException

from app.api import reminder_routes
from app.config import Settings


def test_reminder_get_company_id_rejects_missing_header():
    try:
        reminder_routes.get_company_id(None)
        assert False, "Expected HTTPException for missing company header"
    except Exception as exc:
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 400


def test_reminder_get_company_id_rejects_unknown_company(monkeypatch):
    settings = Settings.model_validate(
        {
            "database": {
                "companies": {
                    "ahf": {"bds_file_path": r"C:\data\ahf.bds"}
                }
            }
        }
    )
    monkeypatch.setattr(reminder_routes, "get_settings", lambda: settings)

    try:
        reminder_routes.get_company_id("unknown")
        assert False, "Expected HTTPException for unknown company id"
    except Exception as exc:
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 404


def test_reminder_get_company_id_accepts_valid_company(monkeypatch):
    settings = Settings.model_validate(
        {
            "database": {
                "companies": {
                    "ahf": {"bds_file_path": r"C:\data\ahf.bds"}
                }
            }
        }
    )
    monkeypatch.setattr(reminder_routes, "get_settings", lambda: settings)

    assert reminder_routes.get_company_id("ahf") == "ahf"
