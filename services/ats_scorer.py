from __future__ import annotations

import re
from typing import Dict, Iterable, List

from services.tailoring_strategy import ADJACENT_PLATFORM_ALIGNMENT, TELECOM_DOMAIN, TailoringStrategy
from services.domain_detector import same_domain
from utils.schema import JobAnalysis, TailoredResume
from utils.technology_terms import extract_known_technologies, is_known_technology
from utils.text import dedupe_keep_order, keyword_match_ratio


TECHNICAL_WEIGHT = 0.65
CLOUD_WEIGHT = 0.20
DOMAIN_WEIGHT = 0.10
FORMAT_WEIGHT = 0.05
LIGHT_DOMAIN_WEIGHT = 0.05

TERM_ALIASES = {
    "Airflow": ["Apache Airflow", "Astronomer", "DAG", "DAG design"],
    "Astronomer": ["Airflow", "Apache Airflow", "DAG", "DAG design"],
    "DAG design": ["Airflow DAG", "DAG design", "DAGs", "orchestration"],
    "performance tuning": ["performance tuning", "throughput tuning", "SQL optimization", "partition strategy", "capacity review"],
    "platform administration": ["platform administration", "platform engineering", "platform services", "configured"],
    "enterprise orchestration": ["enterprise orchestration", "orchestration", "Airflow", "DAG", "workflow"],
    "delivery support": ["delivery support", "production support", "support handoff", "incident response", "runbook"],
    "technical depth": ["technical depth", "hands-on engineering", "core engineering", "production-minded"],
    "reliability": ["reliability", "SLA", "SLO", "alerting", "recovery", "incident response"],
    "advanced Spark": ["Spark", "Apache Spark", "PySpark", "Spark SQL", "Spark Structured Streaming"],
    "Databricks": ["Databricks", "Databricks SQL", "Delta Lake"],
}

DOMAIN_SPECIFIC_TERMS = {
    "HIPAA",
    "PHI",
    "FHIR",
    "HL7",
    "PCI-DSS",
    "SOX",
    "AML",
    "KYC",
    "banking",
    "financial",
    "fraud",
    "regulatory",
    "claims",
    "claims data",
    "patient",
    "patient analytics",
    "clinical",
    "clinical reporting",
    "provider analytics",
    "retail",
    "e-commerce",
    "seller",
    "seller analytics",
    "supply chain",
    "flight",
    "flight operations",
    "airline",
    "booking",
    "booking analytics",
    "itinerary",
    "hotel",
    "telecom",
    "mediation",
    "carrier-grade",
    "CDR",
    "UDR",
    "ASN.1",
    "3GPP",
    "OSS/BSS",
}


def score_resume(
    resume: TailoredResume | None,
    resume_text: str,
    jd: JobAnalysis,
    selected_clouds: Iterable[str],
    tailoring_strategy: TailoringStrategy | None = None,
) -> Dict[str, object]:
    hard_skill_terms = _hard_skill_terms(jd)
    responsibility_terms = _responsibility_key_terms(jd)
    jd_keywords = dedupe_keep_order(hard_skill_terms + responsibility_terms + _scoreable_jd_terms(jd))

    hard_skill_score, hard_matched, hard_missing = _match_terms(hard_skill_terms, resume_text)
    responsibility_score, responsibility_matched, responsibility_missing = _match_terms(responsibility_terms, resume_text)
    keyword_score = _technical_score(hard_skill_score, responsibility_score, hard_skill_terms, responsibility_terms)
    matched = dedupe_keep_order(hard_matched + responsibility_matched)
    missing = dedupe_keep_order(hard_missing + responsibility_missing)

    clouds = dedupe_keep_order(selected_clouds)
    cloud_score, cloud_matched, cloud_missing = _match_terms(clouds, resume_text)

    domain_terms = _scored_domain_terms(jd)
    if domain_terms:
        domain_score, domain_matched, domain_missing = _match_terms(domain_terms, resume_text)
    else:
        domain_score, domain_matched, domain_missing = 100.0, [], []

    domain_weight = DOMAIN_WEIGHT if _has_domain_specific_requirements(domain_terms, tailoring_strategy) else LIGHT_DOMAIN_WEIGHT
    technical_weight = TECHNICAL_WEIGHT + (DOMAIN_WEIGHT - domain_weight)
    overall = round(
        (keyword_score * technical_weight)
        + (cloud_score * CLOUD_WEIGHT)
        + (domain_score * domain_weight)
        + (100.0 * FORMAT_WEIGHT),
        1,
    )
    missing_tools = [kw for kw in hard_missing if _looks_like_tool(kw)]
    missing_general_keywords = [kw for kw in missing if kw not in missing_tools and kw not in domain_missing]
    missing_responsibilities = responsibility_missing

    suggestions = _build_suggestions(
        overall=overall,
        keyword_score=keyword_score,
        cloud_score=cloud_score,
        domain_score=domain_score,
        missing_tools=missing_tools,
        cloud_missing=cloud_missing,
        domain_missing=domain_missing,
        missing_general_keywords=missing_general_keywords + missing_responsibilities,
        tailoring_strategy=tailoring_strategy,
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
        "tailoring_strategy": tailoring_strategy.name if tailoring_strategy else "",
        "domain_gap_warning": _domain_gap_warning(tailoring_strategy),
    }


def _technical_score(
    hard_skill_score: float,
    responsibility_score: float,
    hard_skill_terms: List[str],
    responsibility_terms: List[str],
) -> float:
    if hard_skill_terms and responsibility_terms:
        return round((hard_skill_score * 0.75) + (responsibility_score * 0.25), 1)
    if hard_skill_terms:
        return hard_skill_score
    if responsibility_terms:
        return responsibility_score
    return 100.0


def _match_terms(terms: Iterable[str], resume_text: str) -> tuple[float, List[str], List[str]]:
    keywords = dedupe_keep_order(terms)
    if not keywords:
        return 100.0, [], []
    lower = (resume_text or "").lower()
    matched = [term for term in keywords if _term_in_text(term, lower)]
    missing = [term for term in keywords if term not in matched]
    score = round((len(matched) / max(len(keywords), 1)) * 100, 1)
    return score, matched, missing


def _term_in_text(term: str, lower_resume_text: str) -> bool:
    values = [term] + TERM_ALIASES.get(term, [])
    normalized_resume = _normalize_for_match(lower_resume_text)
    for value in values:
        normalized = _normalize_for_match(value)
        if normalized and normalized in normalized_resume:
            return True
    return False


def _normalize_for_match(value: str) -> str:
    return re.sub(r"[^a-z0-9+#./]+", " ", (value or "").lower()).strip()


def _hard_skill_terms(jd: JobAnalysis) -> List[str]:
    direct = (
        jd.required_skills
        + jd.preferred_skills
        + jd.cloud_platforms
        + jd.data_tools
        + jd.databases
        + jd.orchestration_tools
        + jd.etl_tools
        + jd.streaming_tools
        + jd.ai_ml_tools
        + jd.certifications
        + jd.ats_keywords
    )
    return dedupe_keep_order(extract_known_technologies(" ".join(direct)) + [term for term in direct if is_known_technology(term)])


def _responsibility_key_terms(jd: JobAnalysis) -> List[str]:
    text = " ".join(jd.responsibilities + jd.ats_keywords + jd.required_skills + jd.preferred_skills)
    phrase_patterns = [
        "advanced Spark",
        "performance tuning",
        "platform administration",
        "DAG design",
        "enterprise orchestration",
        "delivery support",
        "technical depth",
        "reliability",
        "data quality",
        "data governance",
        "cost optimization",
        "production support",
        "incident response",
        "root cause analysis",
        "SQL optimization",
        "scalability",
        "data pipelines",
        "pipeline design",
    ]
    found = [phrase for phrase in phrase_patterns if phrase.lower() in text.lower()]
    for responsibility in jd.responsibilities:
        found.extend(_short_key_phrases(responsibility))
    return dedupe_keep_order(found)[:24]


def _short_key_phrases(text: str) -> List[str]:
    clean = re.sub(r"[^A-Za-z0-9+#./ -]+", " ", text or "")
    words = [word for word in clean.split() if len(word) > 2]
    phrases = []
    for size in (2, 3):
        for index in range(max(0, len(words) - size + 1)):
            phrase = " ".join(words[index : index + size])
            if _looks_like_responsibility_phrase(phrase):
                phrases.append(phrase)
    return phrases[:6]


def _looks_like_responsibility_phrase(phrase: str) -> bool:
    lower = phrase.lower()
    signals = [
        "data",
        "pipeline",
        "platform",
        "orchestration",
        "spark",
        "performance",
        "tuning",
        "reliability",
        "support",
        "administration",
        "quality",
        "delivery",
    ]
    return any(signal in lower for signal in signals)


def _scored_domain_terms(jd: JobAnalysis) -> List[str]:
    return dedupe_keep_order(term for term in jd.domain_keywords if term in DOMAIN_SPECIFIC_TERMS)


def _has_domain_specific_requirements(domain_terms: List[str], tailoring_strategy: TailoringStrategy | None) -> bool:
    if tailoring_strategy and tailoring_strategy.name == ADJACENT_PLATFORM_ALIGNMENT:
        return False
    return len(domain_terms) >= 2


def _build_suggestions(
    overall: float,
    keyword_score: float,
    cloud_score: float,
    domain_score: float,
    missing_tools: List[str],
    cloud_missing: List[str],
    domain_missing: List[str],
    missing_general_keywords: List[str],
    tailoring_strategy: TailoringStrategy | None = None,
) -> List[str]:
    suggestions: List[str] = []
    if tailoring_strategy and tailoring_strategy.name == ADJACENT_PLATFORM_ALIGNMENT:
        suggestions.append(_domain_gap_warning(tailoring_strategy))
    if missing_tools:
        suggestions.append(
            "Add truthful missing JD tools to the most recent three experiences first; older experiences should use about half of the JD tools plus strong selected-cloud coverage."
        )
    if cloud_missing:
        suggestions.append("Increase selected-cloud coverage in skills and environment sections.")
    if domain_missing:
        if tailoring_strategy and tailoring_strategy.name == ADJACENT_PLATFORM_ALIGNMENT:
            suggestions.append("Keep unmatched domain terms out of experience claims unless the source resume supports them; emphasize transferable platform, streaming, and reliability work instead.")
        else:
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


def _domain_gap_warning(tailoring_strategy: TailoringStrategy | None) -> str:
    if not tailoring_strategy or tailoring_strategy.name != ADJACENT_PLATFORM_ALIGNMENT:
        return ""
    if same_domain(tailoring_strategy.job_domain, TELECOM_DOMAIN):
        return "No direct telecom client experience detected; tailoring emphasizes truthful streaming, platform engineering, observability, and SRE overlap instead of telecom mediation ownership."
    return f"No direct {tailoring_strategy.job_domain} client experience detected; tailoring emphasizes transferable engineering overlap instead of unsupported domain claims."


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
