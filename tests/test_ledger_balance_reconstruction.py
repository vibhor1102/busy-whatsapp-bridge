from datetime import date
from contextlib import contextmanager
from decimal import Decimal

from app.constants.ledger_constants import VoucherType
from app.models.ledger_schemas import LedgerEntry
from app.services.ledger_data_service import ledger_data_service
from app.services.reminder_snapshot_service import reminder_snapshot_service


def test_determine_dr_cr_maps_debtor_voucher_types_correctly():
    assert ledger_data_service._determine_dr_cr(VoucherType.SALES, 100) is True
    assert ledger_data_service._determine_dr_cr(VoucherType.CREDIT_NOTE, 100) is True
    assert ledger_data_service._determine_dr_cr(VoucherType.PAYMENT_CASH, 100) is True
    assert ledger_data_service._determine_dr_cr(VoucherType.PAYMENT_BANK, 100) is True
    assert ledger_data_service._determine_dr_cr(VoucherType.PAYMENT_CASH, 100, vch_no="CN-60-AHF") is False

    assert ledger_data_service._determine_dr_cr(VoucherType.PURCHASE, 100) is False
    assert ledger_data_service._determine_dr_cr(VoucherType.RECEIPT, 100) is False
    assert ledger_data_service._determine_dr_cr(VoucherType.RECEIPT_ALT, 100) is False
    assert ledger_data_service._determine_dr_cr(VoucherType.DEBIT_NOTE, 100) is False


def test_credit_note_series_uses_credit_note_label():
    assert ledger_data_service._get_voucher_type_name(VoucherType.PAYMENT_CASH, vch_no="CN-60-AHF") == "CrNt"


def test_determine_dr_cr_uses_value_sign_for_journal_like_vouchers():
    assert ledger_data_service._determine_dr_cr(VoucherType.JOURNAL, -100) is True
    assert ledger_data_service._determine_dr_cr(VoucherType.JOURNAL, 100) is False
    assert ledger_data_service._determine_dr_cr(VoucherType.CONTRA, -100) is True
    assert ledger_data_service._determine_dr_cr(VoucherType.CONTRA, 100) is False


def test_snapshot_signed_contribution_matches_debtor_balance_effect():
    assert ledger_data_service._signed_contribution(VoucherType.SALES, Decimal("-100")) == Decimal("100")
    assert ledger_data_service._signed_contribution(VoucherType.SALES, Decimal("100")) == Decimal("-100")
    assert ledger_data_service._signed_contribution(VoucherType.CREDIT_NOTE, Decimal("100")) == Decimal("100")
    assert ledger_data_service._signed_contribution(VoucherType.PAYMENT_CASH, Decimal("100")) == Decimal("100")
    assert ledger_data_service._signed_contribution(VoucherType.PAYMENT_CASH, Decimal("100"), vch_no="CN-60-AHF") == Decimal("-100")

    assert ledger_data_service._signed_contribution(VoucherType.RECEIPT, Decimal("100")) == Decimal("-100")
    assert ledger_data_service._signed_contribution(VoucherType.RECEIPT_ALT, Decimal("100")) == Decimal("-100")
    assert ledger_data_service._signed_contribution(VoucherType.PURCHASE, Decimal("100")) == Decimal("-100")
    assert ledger_data_service._signed_contribution(VoucherType.DEBIT_NOTE, Decimal("100")) == Decimal("-100")


def test_classify_voucher_rows_aggregates_multirow_journal_deterministically():
    amount, is_debit = ledger_data_service._classify_voucher_rows(
        VoucherType.JOURNAL,
        [Decimal("-125"), Decimal("25")],
    )

    assert amount == Decimal("100")
    assert is_debit is True


def test_classify_voucher_rows_aggregates_multirow_receipt_deterministically():
    amount, is_debit = ledger_data_service._classify_voucher_rows(
        VoucherType.RECEIPT,
        [Decimal("80"), Decimal("20")],
    )

    assert amount == Decimal("100")
    assert is_debit is False


def test_build_split_entries_for_mixed_sign_sales_voucher():
    entries = ledger_data_service._build_split_entries_for_voucher(
        vch_code=6921,
        vch_date=date(2025, 9, 27),
        vch_no="AHF-3088",
        vch_type=VoucherType.SALES,
        party_code=33939,
        voucher_rows_lookup={
            6921: [
                {"sr_no": 1, "master_code1": 33939, "master_code2": 0, "value1": Decimal("-77877")},
                {"sr_no": 2, "master_code1": 4, "master_code2": 0, "value1": Decimal("74168.5")},
                {"sr_no": 3, "master_code1": 14928, "master_code2": 0, "value1": Decimal("1854.25")},
                {"sr_no": 4, "master_code1": 14927, "master_code2": 0, "value1": Decimal("1854.25")},
                {"sr_no": 5, "master_code1": 1, "master_code2": 0, "value1": Decimal("-77877")},
                {"sr_no": 6, "master_code1": 33939, "master_code2": 0, "value1": Decimal("77877")},
            ]
        },
        master_name_lookup={
            1: "Cash",
            4: "SALE",
            14927: "SGST",
            14928: "CGST",
        },
    )

    assert entries is not None
    assert [(entry.amount, entry.is_debit, entry.voucher_type, entry.particulars) for entry in entries] == [
        (Decimal("77877"), True, "SupO", "SALE-AHF-3088"),
        (Decimal("77877"), False, "Rcpt", "Cash-AHF-3088"),
    ]


def test_calculate_balances_reconstructs_running_balance_with_notes():
    entries = [
        LedgerEntry(
            date=date(2025, 4, 1),
            particulars="Sale",
            voucher_no="1",
            voucher_type="SupO",
            amount=Decimal("1000"),
            is_debit=True,
            balance=Decimal("0"),
        ),
        LedgerEntry(
            date=date(2025, 4, 2),
            particulars="Debit note",
            voucher_no="2",
            voucher_type="DrNt",
            amount=Decimal("100"),
            is_debit=False,
            balance=Decimal("0"),
        ),
        LedgerEntry(
            date=date(2025, 4, 3),
            particulars="Credit note",
            voucher_no="3",
            voucher_type="CrNt",
            amount=Decimal("50"),
            is_debit=True,
            balance=Decimal("0"),
        ),
        LedgerEntry(
            date=date(2025, 4, 4),
            particulars="Receipt",
            voucher_no="4",
            voucher_type="Rcpt",
            amount=Decimal("300"),
            is_debit=False,
            balance=Decimal("0"),
        ),
    ]

    total_debits, total_credits = ledger_data_service.calculate_balances(Decimal("0"), entries)

    assert total_debits == Decimal("1050")
    assert total_credits == Decimal("400")
    assert [entry.balance for entry in entries] == [
        Decimal("1000"),
        Decimal("900"),
        Decimal("950"),
        Decimal("650"),
    ]


def test_get_opening_balance_uses_d1_plus_d4(monkeypatch):
    class FakeCursor:
        def __init__(self):
            self.last_query = ""

        def execute(self, _query):
            self.last_query = _query
            return None

        def fetchone(self):
            if "FROM Folio1" in self.last_query:
                return (100, -25)
            if "SELECT ParentGrp" in self.last_query:
                return (116,)
            return None

    @contextmanager
    def fake_get_cursor(company_id="default"):
        yield FakeCursor()

    monkeypatch.setattr(ledger_data_service.db, "get_cursor", fake_get_cursor)

    balance = ledger_data_service.get_opening_balance("123", date(2025, 4, 1))

    assert balance == Decimal("100")


def test_get_opening_balance_flips_creditor_group_to_cr(monkeypatch):
    class FakeCursor:
        def __init__(self):
            self.last_query = ""

        def execute(self, query):
            self.last_query = query
            return None

        def fetchone(self):
            if "FROM Folio1" in self.last_query:
                return (1181895, 1181895)
            if "SELECT ParentGrp" in self.last_query:
                return (117,)
            return None

    @contextmanager
    def fake_get_cursor(company_id="default"):
        yield FakeCursor()

    monkeypatch.setattr(ledger_data_service.db, "get_cursor", fake_get_cursor)

    balance = ledger_data_service.get_opening_balance("26967", date(2025, 4, 1))

    assert balance == Decimal("-1181895")
