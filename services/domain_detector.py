from __future__ import annotations

from typing import Dict, Iterable, List

from services.client_registry import known_client_domain
from utils.schema import JobAnalysis


CLIENT_DOMAINS: Dict[str, str] = {
}

ENTERPRISE_DOMAIN = "Enterprise Data Engineering"

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "Healthcare": [
        "HIPAA",
        "PHI",
        "patient analytics",
        "claims data",
        "clinical reporting",
        "FHIR",
        "HL7",
        "provider analytics",
        "healthcare compliance",
        "pharmacy data",
    ],
    "Financial Services / Banking / Wealth Management / Asset Servicing": [
        "PCI-DSS",
        "SOX",
        "AML",
        "KYC",
        "wealth management",
        "asset servicing",
        "fraud detection",
        "risk analytics",
        "regulatory reporting",
        "audit controls",
        "transaction processing",
    ],
    "Retail / E-commerce": [
        "inventory optimization",
        "customer analytics",
        "order pipelines",
        "recommendation systems",
        "pricing analytics",
        "supply chain",
        "seller analytics",
    ],
    "Aviation": [
        "flight operations",
        "aircraft maintenance data",
        "crew scheduling",
        "loyalty analytics",
        "route optimization",
        "passenger analytics",
        "safety reporting",
    ],
    "Travel / Online Travel Platform": [
        "booking analytics",
        "itinerary data",
        "hotel and flight search",
        "cancellation analytics",
        "recommendation systems",
        "pricing trends",
        "customer segmentation",
    ],
}

DOMAIN_SIGNALS: Dict[str, List[str]] = {
    "Healthcare": [
        "healthcare",
        "health care",
        "clinical",
        "patient",
        "provider",
        "claims",
        "hipaa",
        "phi",
        "fhir",
        "hl7",
        "pharmacy",
        "medical",
        "payer",
    ],
    "Financial Services / Banking / Wealth Management / Asset Servicing": [
        "finance",
        "financial",
        "bank",
        "banking",
        "wealth",
        "asset servicing",
        "risk",
        "fraud",
        "aml",
        "kyc",
        "sox",
        "pci",
        "transaction",
        "regulatory",
    ],
    "Retail / E-commerce": [
        "retail",
        "ecommerce",
        "e-commerce",
        "seller",
        "inventory",
        "order",
        "pricing",
        "supply chain",
        "customer analytics",
    ],
    "Aviation": [
        "aviation",
        "airline",
        "flight",
        "aircraft",
        "crew",
        "route",
        "passenger",
        "safety",
    ],
    "Travel / Online Travel Platform": [
        "travel",
        "booking",
        "hotel",
        "itinerary",
        "trip",
        "cancellation",
        "reservation",
    ],
}


def detect_domain(client_name: str, resume_text: str = "") -> str:
    known_domain = known_client_domain(client_name)
    if known_domain:
        return known_domain

    client_lower = (client_name or "").lower()
    for key, domain in CLIENT_DOMAINS.items():
        if key in client_lower:
            return domain

    text = f"{client_name} {resume_text}".lower()
    for domain, terms in DOMAIN_SIGNALS.items():
        if any(term in text for term in terms):
            return domain
    return ENTERPRISE_DOMAIN


def infer_job_domain(jd: JobAnalysis) -> str:
    """Infer the target JD domain from extracted domain terms and JD phrases."""
    text = _domain_evidence_text(
        jd.domain_keywords,
        jd.required_skills,
        jd.preferred_skills,
        jd.ats_keywords,
        jd.responsibilities,
    )
    if not text:
        return ENTERPRISE_DOMAIN

    scores: Dict[str, int] = {}
    for domain, signals in DOMAIN_SIGNALS.items():
        score = 0
        for signal in signals:
            if signal.lower() in text:
                score += 2
        for keyword in DOMAIN_KEYWORDS.get(domain, []):
            if keyword.lower() in text:
                score += 3
        scores[domain] = score

    best_domain = max(scores, key=scores.get)
    return best_domain if scores[best_domain] > 0 else ENTERPRISE_DOMAIN


def is_enterprise_domain(domain: str) -> bool:
    return not domain or domain == ENTERPRISE_DOMAIN


def same_domain(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left.lower() == right.lower() or left.lower() in right.lower() or right.lower() in left.lower()


def keywords_for_domain(domain: str) -> List[str]:
    if domain in DOMAIN_KEYWORDS:
        return DOMAIN_KEYWORDS[domain]
    for known, keywords in DOMAIN_KEYWORDS.items():
        if known.lower() in domain.lower() or domain.lower() in known.lower():
            return keywords
    return ["enterprise analytics", "data governance", "operational reporting", "data quality"]


def _domain_evidence_text(*groups: Iterable[str]) -> str:
    values: List[str] = []
    for group in groups:
        values.extend(str(value) for value in group if value)
    return " ".join(values).lower()
