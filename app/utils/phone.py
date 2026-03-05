"""
Phone normalization helpers for WhatsApp providers.
"""

from __future__ import annotations

import re


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_indian_phone_local(raw_phone: str) -> str:
    """Normalize arbitrary input to an Indian 10-digit mobile number."""
    if raw_phone is None:
        raise ValueError("phone is required")

    value = str(raw_phone).strip()
    if not value:
        raise ValueError("phone is empty")

    value = value.replace("whatsapp:", "")

    digits = _digits_only(value)
    if not digits:
        raise ValueError(f"phone has no digits: {raw_phone!r}")

    while len(digits) > 10 and digits.startswith("0"):
        digits = digits[1:]
    while len(digits) > 10 and digits.startswith("91"):
        digits = digits[2:]

    if len(digits) > 10:
        digits = digits[-10:]

    if len(digits) != 10:
        raise ValueError(f"phone length invalid after normalization: {raw_phone!r}")

    if digits[0] not in {"6", "7", "8", "9"}:
        raise ValueError(f"phone is not a valid Indian mobile number: {raw_phone!r}")

    return digits


def normalize_phone_e164(raw_phone: str, default_country_code: str = "91") -> str:
    """Normalize arbitrary input to +91XXXXXXXXXX format (India-only)."""
    _ = default_country_code  # Preserved for backward-compatible call sites.
    local = normalize_indian_phone_local(raw_phone)
    return f"+91{local}"


def to_wa_id(e164_or_raw: str, default_country_code: str = "91") -> str:
    """Return WhatsApp ID numeric format without '+'."""
    return _digits_only(normalize_phone_e164(e164_or_raw, default_country_code))

