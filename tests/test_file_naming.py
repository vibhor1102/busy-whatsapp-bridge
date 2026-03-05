from datetime import datetime

from app.utils.file_naming import build_pdf_filename, sanitize_filename_token


def test_sanitize_filename_token_normalizes_and_filters():
    assert sanitize_filename_token("  ACME & Sons Pvt. Ltd.  ") == "acme_sons_pvt_ltd"
    assert sanitize_filename_token("Müller ट्रेडर्स") == "muller"
    assert sanitize_filename_token("___") is None
    assert sanitize_filename_token("") is None


def test_build_pdf_filename_with_customer_name():
    now = datetime(2026, 3, 5, 10, 0, 0)
    assert (
        build_pdf_filename(kind="invoice", customer_name="ABC Traders", now=now)
        == "abc_traders_invoice_05-03-2026.pdf"
    )
    assert (
        build_pdf_filename(kind="ledger", customer_name="A&B/Co.", now=now)
        == "a_b_co_ledger_05-03-2026.pdf"
    )


def test_build_pdf_filename_fallback_without_customer_name():
    now = datetime(2026, 3, 5, 10, 0, 0)
    assert build_pdf_filename(kind="invoice", customer_name=None, now=now) == "invoice_05-03-2026.pdf"
    assert build_pdf_filename(kind="ledger", customer_name="   ", now=now) == "ledger_05-03-2026.pdf"
