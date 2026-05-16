from __future__ import annotations

from typing import Dict, Iterable, List

from utils.schema import JobAnalysis, TailoredResume
from utils.technology_terms import is_known_technology
from utils.text import dedupe_keep_order, keyword_match_ratio


def score_resume(resume: TailoredResume | None, resume_text: str, jd: JobAnalysis, selected_clouds: Iterable[str]) -> Dict[str, object]:
    jd_keywords = _scoreable_jd_terms(jd)
    keyword_score, matched, missing = keyword_match_ratio(jd_keywords, resume_text)

    clouds = dedupe_keep_order(selected_clouds)
    cloud_score, cloud_matched, cloud_missing = keyword_match_ratio(clouds, resume_text)

    if jd.domain_keywords:
        domain_score, domain_matched, domain_missing = keyword_match_ratio(jd.domain_keywords, resume_text)
    else:
        domain_score, domain_matched, domain_missing = 100.0, [], []

    overall = round((keyword_score * 0.65) + (cloud_score * 0.2) + (domain_score * 0.15), 1)
    missing_tools = [kw for kw in missing if _looks_like_tool(kw)]
    missing_general_keywords = [kw for kw in missing if kw not in missing_tools and kw not in domain_missing]
    missing_responsibilities = _missing_responsibility_terms(jd.responsibilities, resume_text)

    suggestions = _build_suggestions(
        overall=overall,
        keyword_score=keyword_score,
        cloud_score=cloud_score,
        domain_score=domain_score,
        missing_tools=missing_tools,
        cloud_missing=cloud_missing,
        domain_missing=domain_missing,
        missing_general_keywords=missing_general_keywords + missing_responsibilities,
    )

    score_breakdown = {
        "overall": _score_rating(overall),
        "technical": _score_rating(keyword_score),
        "cloud": _score_rating(cloud_score),
        "domain": _score_rating(domain_score),
    }

    priority_gaps = _priority_gaps(missing_tools, domain_missing, cloud_missing, missing_general_keywords, missing_responsibilities)

    return {
        "ats_match_percentage": overall,
        "keyword_score": keyword_score,
        "cloud_alignment_score": cloud_score,
        "domain_alignment_score": domain_score,
        "score_breakdown": score_breakdown,
        "priority_gaps": priority_gaps,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "missing_tools": missing_tools,
        "missing_general_keywords": missing_general_keywords,
        "missing_responsibilities": missing_responsibilities,
        "cloud_matched": cloud_matched,
        "cloud_missing": cloud_missing,
        "domain_matched": domain_matched,
        "domain_missing": domain_missing,
        "suggestions": suggestions,
    }


def _build_suggestions(
    overall: float,
    keyword_score: float,
    cloud_score: float,
    domain_score: float,
    missing_tools: List[str],
    cloud_missing: List[str],
    domain_missing: List[str],
    missing_general_keywords: List[str],
) -> List[str]:
    suggestions: List[str] = []
    if missing_tools:
        suggestions.append(
            "Add truthful missing JD tools to the most recent three experiences first; older experiences should use about half of the JD tools plus strong selected-cloud coverage."
        )
    if cloud_missing:
        suggestions.append("Increase selected-cloud coverage in skills and environment sections.")
    if domain_missing:
        suggestions.append("Add missing domain terms naturally to recent experience bullets and the professional summary.")
    if missing_general_keywords and keyword_score < 70:
        suggestions.append("Blend important missing responsibility phrases into bullets without keyword stuffing.")
    if keyword_score < 70:
        suggestions.append("Technical match is the largest score driver; prioritize JD-required tools and data engineering responsibilities.")
    if cloud_score < 90:
        suggestions.append("Cloud alignment should usually be 90% or higher after selecting cloud platforms for each client.")
    if domain_score < 70:
        suggestions.append("Domain alignment should usually be 70% or higher for domain-specific JDs.")
    if overall >= 85:
        suggestions.append("Resume is strongly aligned; review for truthfulness and final formatting polish.")
    elif overall >= 70:
        suggestions.append("Resume is moderately aligned; close the highest-priority missing technical and domain gaps before applying.")
    else:
        suggestions.append("Resume needs more tailoring before applying; focus on JD tools, recent experience bullets, and domain language.")
    return suggestions


def _score_rating(score: float) -> str:
    if score >= 85:
        return "Strong"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Needs work"
    return "Weak"


def _priority_gaps(
    missing_tools: List[str],
    domain_missing: List[str],
    cloud_missing: List[str],
    missing_general_keywords: List[str],
    missing_responsibilities: List[str],
) -> Dict[str, List[str]]:
    responsibility_terms = dedupe_keep_order(_shorten_gap(item) for item in missing_general_keywords + missing_responsibilities)
    return {
        "technical_tools": missing_tools[:20],
        "domain_terms": domain_missing[:20],
        "cloud_terms": cloud_missing[:20],
        "responsibility_terms": responsibility_terms[:20],
    }


def _scoreable_jd_terms(jd: JobAnalysis) -> List[str]:
    terms: List[str] = []
    for field, value in jd.__dict__.items():
        if field == "responsibilities":
            continue
        if isinstance(value, list):
            terms.extend(term for term in value if _is_scoreable_term(str(term)))
    return dedupe_keep_order(terms)


def _is_scoreable_term(value: str) -> bool:
    words = value.split()
    return bool(value.strip()) and len(words) <= 8


def _missing_responsibility_terms(responsibilities: Iterable[str], resume_text: str) -> List[str]:
    lower = (resume_text or "").lower()
    missing: List[str] = []
    for responsibility in responsibilities:
        clean = " ".join(str(responsibility).split())
        if clean and clean.lower() not in lower:
            missing.append(clean)
    return missing[:8]


def _shorten_gap(value: str, maximum_words: int = 12) -> str:
    words = value.split()
    if len(words) <= maximum_words:
        return value
    return " ".join(words[:maximum_words]).rstrip(".,;") + "..."


def _looks_like_tool(keyword: str) -> bool:
    return is_known_technology(keyword)
