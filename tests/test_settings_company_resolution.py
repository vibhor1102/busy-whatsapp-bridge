from app.config import Settings


def test_get_database_connection_string_falls_back_from_default_to_first_company():
    settings = Settings(
        database={
            "companies": {
                "ahf": {
                    "bds_file_path": r"C:\data\company_ahf.bds",
                    "bds_password": "secret",
                }
            }
        }
    )

    conn_str = settings.get_database_connection_string("default")

    assert "DBQ=C:\\data\\company_ahf.bds;" in conn_str
    assert "PWD=secret;" in conn_str
    assert "Mode=Read;" not in conn_str


def test_resolve_company_id_prefers_existing_requested_company():
    settings = Settings(
        database={
            "companies": {
                "ahf": {"bds_file_path": r"C:\data\company_ahf.bds"},
                "xyz": {"bds_file_path": r"C:\data\company_xyz.bds"},
            }
        }
    )

    assert settings.resolve_company_id("xyz") == "xyz"
