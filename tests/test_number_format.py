from decimal import Decimal

from app.utils.number_format import format_indian_currency, format_indian_number


def test_format_indian_number_groups_correctly():
    assert format_indian_number(1234567.89) == "12,34,567.89"


def test_format_indian_number_handles_negative_values():
    assert format_indian_number(Decimal("-9876543.2")) == "-98,76,543.20"


def test_format_indian_currency_prefixes_symbol():
    assert format_indian_currency(12345, symbol="₹") == "₹12,345.00"
