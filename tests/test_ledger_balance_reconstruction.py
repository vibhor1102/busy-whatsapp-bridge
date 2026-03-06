from datetime import date
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

    assert ledger_data_service._determine_dr_cr(VoucherType.PURCHASE, 100) is False
    assert ledger_data_service._determine_dr_cr(VoucherType.RECEIPT, 100) is False
    assert ledger_data_service._determine_dr_cr(VoucherType.RECEIPT_ALT, 100) is False
    assert ledger_data_service._determine_dr_cr(VoucherType.DEBIT_NOTE, 100) is False


def test_determine_dr_cr_uses_value_sign_for_journal_like_vouchers():
    assert ledger_data_service._determine_dr_cr(VoucherType.JOURNAL, -100) is True
    assert ledger_data_service._determine_dr_cr(VoucherType.JOURNAL, 100) is False
    assert ledger_data_service._determine_dr_cr(VoucherType.CONTRA, -100) is True
    assert ledger_data_service._determine_dr_cr(VoucherType.CONTRA, 100) is False


def test_snapshot_signed_contribution_matches_debtor_balance_effect():
    assert reminder_snapshot_service._signed_contribution(VoucherType.SALES, Decimal("100")) == Decimal("100")
    assert reminder_snapshot_service._signed_contribution(VoucherType.CREDIT_NOTE, Decimal("100")) == Decimal("100")
    assert reminder_snapshot_service._signed_contribution(VoucherType.PAYMENT_CASH, Decimal("100")) == Decimal("100")

    assert reminder_snapshot_service._signed_contribution(VoucherType.RECEIPT, Decimal("100")) == Decimal("-100")
    assert reminder_snapshot_service._signed_contribution(VoucherType.RECEIPT_ALT, Decimal("100")) == Decimal("-100")
    assert reminder_snapshot_service._signed_contribution(VoucherType.PURCHASE, Decimal("100")) == Decimal("-100")
    assert reminder_snapshot_service._signed_contribution(VoucherType.DEBIT_NOTE, Decimal("100")) == Decimal("-100")


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
