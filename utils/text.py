from __future__ import annotations

import re
from collections import OrderedDict
from typing import Iterable, List


SECTION_ALIASES = {
    "summary": ["professional summary", "summary", "profile"],
    "skills": ["technical skills", "skills", "technologies"],
    "experience": ["professional experience", "work experience", "experience", "client experience"],
    "certifications": ["certifications", "certification"],
    "education": ["education", "academic"],
}


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def dedupe_keep_order(items: Iterable[str]) -> List[str]:
    seen = OrderedDict()
    for item in items:
        normalized = re.sub(r"\s+", " ", str(item).strip())
        if normalized and normalized.lower() not in seen:
            seen[normalized.lower()] = normalized
    return list(seen.values())


def words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9+#./-]{1,}", text or "")


def keyword_match_ratio(source: Iterable[str], target_text: str) -> tuple[float, List[str], List[str]]:
    keywords = dedupe_keep_order(source)
    lower = (target_text or "").lower()
    matched = [kw for kw in keywords if kw.lower() in lower]
    missing = [kw for kw in keywords if kw.lower() not in lower]
    score = round((len(matched) / max(len(keywords), 1)) * 100, 1)
    return score, matched, missing


def split_csvish(text: str) -> List[str]:
    parts = re.split(r"[,;|/]|\n| - ", text or "")
    return dedupe_keep_order(part.strip(" .:-") for part in parts)


def clamp_words(sentence: str, minimum: int = 28, maximum: int = 32) -> str:
    tokens = sentence.strip().rstrip(".").split()
    if len(tokens) > maximum:
        tokens = tokens[:maximum]
    return " ".join(tokens).rstrip(",;") + "."
