"""
Phone normalization helpers for WhatsApp providers.
"""

from __future__ import annotations

import re
from typing import Optional


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_phone_e164(raw_phone: str, default_country_code: str = "91") -> str:
    """
    Normalize arbitrary phone text to E.164 format.

    Rules:
    - Preserves explicit international input (+ or 00 prefix).
    - For local 10-digit numbers, prefixes default_country_code.
    - For local 11-digit numbers starting with 0, drops leading 0 and prefixes default_country_code.
    """
    if raw_phone is None:
        raise ValueError("phone is required")

    value = str(raw_phone).strip()
    if not value:
        raise ValueError("phone is empty")

    value = value.replace("whatsapp:", "").strip()

    explicit_international = value.startswith("+") or value.startswith("00")
    if value.startswith("00"):
        value = "+" + value[2:]

    digits = _digits_only(value)
    if not digits:
        raise ValueError(f"phone has no digits: {raw_phone!r}")

    cc = _digits_only(default_country_code or "")
    if not cc:
        cc = "91"

    if not explicit_international:
        if len(digits) == 11 and digits.startswith("0"):
            digits = cc + digits[1:]
        elif len(digits) == 10:
            digits = cc + digits
        elif len(digits) == len(cc) + 10 and digits.startswith(cc):
            pass

    if len(digits) < 8 or len(digits) > 15:
        raise ValueError(f"phone length invalid after normalization: {raw_phone!r}")

    return f"+{digits}"


def to_wa_id(e164_or_raw: str, default_country_code: str = "91") -> str:
    """Return WhatsApp ID numeric format without '+'."""
    return _digits_only(normalize_phone_e164(e164_or_raw, default_country_code))

