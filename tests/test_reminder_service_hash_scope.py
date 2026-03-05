from decimal import Decimal
from types import SimpleNamespace

from app.services.reminder_service import ReminderService


def test_get_eligible_parties_page_uses_selected_company_db_hash(monkeypatch):
    service = ReminderService()

    fake_settings = SimpleNamespace(
        BDS_FILE_PATH=r"C:\data\global_default.bds",
        database=SimpleNamespace(
            bds_file_path=r"C:\data\global_default.bds",
            companies={
                "company_a": SimpleNamespace(bds_file_path=r"C:\data\company_a.bds"),
            },
        ),
    )
    service.calculator.db.settings = fake_settings

    # This hash corresponds to company_a path and must be treated as fresh.
    import hashlib
    company_hash = hashlib.sha256(r"C:\data\company_a.bds".encode("utf-8")).hexdigest()
    monkeypatch.setattr(
        service.snapshot_db,
        "get_status",
        lambda company_id="default": {"has_snapshot": True, "source_db_path_hash": company_hash},
    )
    monkeypatch.setattr(
        service.snapshot_db,
        "query_parties",
        lambda **kwargs: (
            1,
            [
                {
                    "party_code": "101",
                    "name": "Test Party",
                    "print_name": "Test Party",
                    "phone": "9999999999",
                    "closing_balance": 1000,
                    "amount_due": 500,
                    "sales_credit_days": 30,
                    "credit_days_source": "master1_i2",
                    "permanent_enabled": 1,
                }
            ],
        ),
    )
    monkeypatch.setattr(
        service.config_service,
        "get_config",
        lambda scope_key=None: SimpleNamespace(currency_symbol="₹"),
    )

    page = service.get_eligible_parties_page(
        min_amount_due=Decimal("0.01"),
        include_zero=False,
        filter_by="all",
        offset=0,
        limit=10,
        company_id="company_a",
    )

    assert page["total"] == 1
    assert len(page["items"]) == 1
