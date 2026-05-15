from __future__ import annotations

from typing import Dict, Iterable, List

from parsers.jd_analyzer import all_jd_terms
from utils.schema import JobAnalysis, TailoredResume
from utils.text import dedupe_keep_order, keyword_match_ratio


def score_resume(resume: TailoredResume | None, resume_text: str, jd: JobAnalysis, selected_clouds: Iterable[str]) -> Dict[str, object]:
    jd_keywords = all_jd_terms(jd)
    keyword_score, matched, missing = keyword_match_ratio(jd_keywords, resume_text)

    clouds = dedupe_keep_order(selected_clouds)
    cloud_score, cloud_matched, cloud_missing = keyword_match_ratio(clouds, resume_text)

    domain_score, domain_matched, domain_missing = keyword_match_ratio(jd.domain_keywords, resume_text)

    overall = round((keyword_score * 0.65) + (cloud_score * 0.2) + (domain_score * 0.15), 1)
    missing_tools = [kw for kw in missing if _looks_like_tool(kw)]

    suggestions: List[str] = []
    if missing_tools:
        suggestions.append("Add missing tools where they are truthful and consistent with the experience timeline.")
    if cloud_missing:
        suggestions.append("Increase cloud-specific service coverage in skills and environment sections.")
    if domain_missing:
        suggestions.append("Add natural domain terminology from the job description to recent experience bullets.")
    if overall >= 85:
        suggestions.append("Resume is strongly aligned; review for truthfulness and final formatting polish.")

    return {
        "ats_match_percentage": overall,
        "keyword_score": keyword_score,
        "cloud_alignment_score": cloud_score,
        "domain_alignment_score": domain_score,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "missing_tools": missing_tools,
        "cloud_matched": cloud_matched,
        "cloud_missing": cloud_missing,
        "domain_matched": domain_matched,
        "domain_missing": domain_missing,
        "suggestions": suggestions,
    }


def _looks_like_tool(keyword: str) -> bool:
    return any(char.isupper() for char in keyword) or keyword.lower() in {
        "spark",
        "airflow",
        "kafka",
        "snowflake",
        "databricks",
        "terraform",
        "docker",
        "kubernetes",
    }
