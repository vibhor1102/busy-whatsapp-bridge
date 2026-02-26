from pathlib import Path

from app.database.reminder_snapshot import ReminderSnapshotDB


def _seed_rows():
    return [
        {
            "party_code": "100",
            "name": "Alpha Traders",
            "print_name": "Alpha",
            "phone": "9999991000",
            "closing_balance": 1000,
            "recent_sales_total": 100,
            "amount_due": 900,
            "sales_credit_days": 30,
            "credit_days_source": "master1_i2",
            "permanent_enabled": True,
        },
        {
            "party_code": "101",
            "name": "Beta Stores",
            "print_name": "Beta",
            "phone": "9999991001",
            "closing_balance": 250,
            "recent_sales_total": 250,
            "amount_due": 0,
            "sales_credit_days": 15,
            "credit_days_source": "config_default",
            "permanent_enabled": False,
        },
        {
            "party_code": "102",
            "name": "Gamma Agency",
            "print_name": "Gamma",
            "phone": "9999991002",
            "closing_balance": 500,
            "recent_sales_total": 50,
            "amount_due": 450,
            "sales_credit_days": 45,
            "credit_days_source": "master1_i2",
            "permanent_enabled": False,
        },
    ]


def test_query_parties_default_hides_zero(tmp_path: Path):
    db = ReminderSnapshotDB(str(tmp_path / "snapshot.db"))
    db.replace_snapshot(
        _seed_rows(),
        duration_ms=1200,
        row_count=3,
        nonzero_count=2,
        error_count=0,
        source_db_path_hash="hash",
    )

    total, rows = db.query_parties(
        search=None,
        filter_by="all",
        min_amount=None,
        include_zero=False,
        sort_by="amount_due",
        sort_order="desc",
        offset=0,
        limit=100,
    )

    assert total == 2
    assert [r["party_code"] for r in rows] == ["100", "102"]


def test_query_parties_include_zero_and_pagination(tmp_path: Path):
    db = ReminderSnapshotDB(str(tmp_path / "snapshot.db"))
    db.replace_snapshot(
        _seed_rows(),
        duration_ms=1000,
        row_count=3,
        nonzero_count=2,
        error_count=0,
        source_db_path_hash="hash",
    )

    total, rows = db.query_parties(
        search=None,
        filter_by="all",
        min_amount=None,
        include_zero=True,
        sort_by="name",
        sort_order="asc",
        offset=1,
        limit=1,
    )

    assert total == 3
    assert len(rows) == 1
    assert rows[0]["name"] == "Beta Stores"


def test_query_parties_filter_enabled(tmp_path: Path):
    db = ReminderSnapshotDB(str(tmp_path / "snapshot.db"))
    db.replace_snapshot(
        _seed_rows(),
        duration_ms=900,
        row_count=3,
        nonzero_count=2,
        error_count=0,
        source_db_path_hash="hash",
    )

    total, rows = db.query_parties(
        search=None,
        filter_by="enabled",
        min_amount=None,
        include_zero=True,
        sort_by="code",
        sort_order="asc",
        offset=0,
        limit=50,
    )

    assert total == 1
    assert rows[0]["party_code"] == "100"
