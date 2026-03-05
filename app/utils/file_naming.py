import re
import unicodedata
from datetime import datetime
from typing import Optional


_SAFE_CHAR_PATTERN = re.compile(r"[^a-z0-9_]+")
_UNDERSCORE_PATTERN = re.compile(r"_+")


def sanitize_filename_token(value: Optional[str]) -> Optional[str]:
    """Sanitize a value for safe filename usage."""
    if not value:
        return None

    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    safe = _SAFE_CHAR_PATTERN.sub("_", ascii_value).strip("_")
    safe = _UNDERSCORE_PATTERN.sub("_", safe)
    return safe or None


def build_pdf_filename(
    kind: str,
    customer_name: Optional[str] = None,
    now: Optional[datetime] = None,
) -> str:
    """Build deterministic invoice/ledger PDF filename."""
    current = now or datetime.now()
    date_part = current.strftime("%d-%m-%Y")

    safe_kind = sanitize_filename_token(kind) or "document"
    safe_name = sanitize_filename_token(customer_name)
    if safe_name:
        return f"{safe_name}_{safe_kind}_{date_part}.pdf"
    return f"{safe_kind}_{date_part}.pdf"
