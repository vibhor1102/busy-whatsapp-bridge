"""
Number formatting helpers.
"""
from decimal import Decimal, InvalidOperation
from typing import Union


NumberLike = Union[int, float, Decimal, str]


def format_indian_number(value: NumberLike, decimal_places: int = 2) -> str:
    """Format a number with Indian digit grouping (e.g. 12,34,567.89)."""
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    sign = "-" if decimal_value < 0 else ""
    absolute_value = abs(decimal_value)

    fixed = f"{absolute_value:.{decimal_places}f}"
    int_part, frac_part = fixed.split(".")

    if len(int_part) <= 3:
        grouped = int_part
    else:
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        grouped = ",".join(reversed(groups)) + "," + last_three

    return f"{sign}{grouped}.{frac_part}"


def format_indian_currency(value: NumberLike, symbol: str = "₹", decimal_places: int = 2) -> str:
    """Format currency with Indian digit grouping."""
    return f"{symbol}{format_indian_number(value, decimal_places=decimal_places)}"
