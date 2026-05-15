from __future__ import annotations

import re
from typing import Iterable, List

from services.cloud_catalog import cloud_timeline_blocklist
from utils.text import dedupe_keep_order


def earliest_year(dates: str) -> int:
    years = [int(y) for y in re.findall(r"(19|20)\d{2}", dates or "")]
    if not years:
        return 2024
    return min(years)


def filter_timeline_safe(technologies: Iterable[str], dates: str) -> List[str]:
    blocked = {term.lower() for term in cloud_timeline_blocklist(earliest_year(dates))}
    return [tech for tech in dedupe_keep_order(technologies) if tech.lower() not in blocked]


def strip_timeline_unsafe_text(text: str, dates: str) -> str:
    cleaned = text
    for blocked in cloud_timeline_blocklist(earliest_year(dates)):
        cleaned = re.sub(rf"\b{re.escape(blocked)}\b,?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r",\s*,", ",", cleaned)
    return cleaned.strip(" ,")
