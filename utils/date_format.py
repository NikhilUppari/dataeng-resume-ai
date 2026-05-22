from __future__ import annotations

import re


DATE_SEPARATOR_PATTERN = r"(?:-|\u2013|\u2014|\u00e2\u20ac\u201c|\u00e2\u20ac\u009d|\bto\b)"
MONTH_NORMALIZATION = {
    "jan": "January",
    "january": "January",
    "feb": "February",
    "february": "February",
    "mar": "March",
    "march": "March",
    "apr": "April",
    "april": "April",
    "may": "May",
    "jun": "June",
    "june": "June",
    "jul": "July",
    "july": "July",
    "aug": "August",
    "august": "August",
    "sep": "September",
    "sept": "September",
    "september": "September",
    "oct": "October",
    "october": "October",
    "nov": "November",
    "november": "November",
    "dec": "December",
    "december": "December",
}


def normalize_display_dates(value: str) -> str:
    normalized = re.sub(r"\bOc\s*-\s*ber\b", "October", value or "", flags=re.IGNORECASE)
    normalized = re.sub(rf"\s*{DATE_SEPARATOR_PATTERN}\s*", " - ", normalized.strip(), flags=re.IGNORECASE)
    normalized = re.sub(r"\b(current|now)\b", "Present", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bpresent\b", "Present", normalized, flags=re.IGNORECASE)
    normalized = re.sub(
        r"\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)\.?\b",
        lambda match: MONTH_NORMALIZATION[match.group(1).lower()],
        normalized,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", normalized)
