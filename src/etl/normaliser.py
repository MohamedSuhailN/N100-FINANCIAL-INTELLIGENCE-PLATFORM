import re
from datetime import date
from typing import Any


def normalize_ticker(ticker: Any) -> str:
    """Normalize a stock ticker by stripping whitespace and exchange suffixes."""
    if ticker is None or not isinstance(ticker, str):
        return ""

    cleaned = ticker.strip()
    if not cleaned:
        return ""

    cleaned = re.sub(r"(?i)^(?:nse|bse)\s*[:\-/]?\s*", "", cleaned)
    cleaned = cleaned.replace("-", "").replace("/", "").replace(".", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.upper()


def normalize_year(year_val: Any) -> int | None:
    """Extract a valid 4-digit year from finance-style strings, floats, and dates."""
    if year_val is None:
        return None

    if isinstance(year_val, date):
        return year_val.year

    if isinstance(year_val, (int, float)):
        if isinstance(year_val, float) and not year_val.is_integer():
            year_val = int(year_val)
        year = int(year_val)
        if 1900 <= year <= 2099:
            return year
        return None

    val_str = str(year_val).strip()
    if not val_str:
        return None

    val_str = re.sub(r"(?i)\b(?:nse|bse)\b", " ", val_str)
    val_str = val_str.replace("FY", "").replace("fy", "")
    matches = re.findall(r"(19\d\d|20\d\d)", val_str)
    if not matches:
        return None
    return int(matches[-1])


def normalize_company_name(value: Any) -> str:
    """Trim and normalize a company name while preserving original casing."""
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def normalize_currency(value: Any) -> float | None:
    """Convert currency strings into numeric floats while tolerating nulls."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    cleaned = str(value).strip().replace(",", "").replace("₹", "").replace("$", "")
    if cleaned in {"", "-", "--", "nan", "NaN", "None", "null"}:
        return None

    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def normalize_percentage(value: Any) -> float | None:
    """Convert percentage-like values to a numeric float."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    cleaned = str(value).strip().replace("%", "")
    if cleaned in {"", "-", "--", "nan", "NaN", "None", "null"}:
        return None

    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None