from __future__ import annotations

from typing import Dict, List

from services.client_registry import known_client_domain


CLIENT_DOMAINS: Dict[str, str] = {
}

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


def detect_domain(client_name: str, resume_text: str = "") -> str:
    known_domain = known_client_domain(client_name)
    if known_domain:
        return known_domain

    client_lower = (client_name or "").lower()
    for key, domain in CLIENT_DOMAINS.items():
        if key in client_lower:
            return domain

    text = f"{client_name} {resume_text}".lower()
    weighted = {
        "Healthcare": ["health", "patient", "clinical", "claims", "hipaa", "provider"],
        "Financial Services / Banking / Wealth Management / Asset Servicing": [
            "bank",
            "finance",
            "trading",
            "wealth",
            "risk",
            "asset",
            "aml",
            "kyc",
        ],
        "Retail / E-commerce": ["retail", "ecommerce", "seller", "inventory", "order", "pricing"],
        "Aviation": ["airline", "flight", "crew", "aircraft", "aviation"],
        "Travel / Online Travel Platform": ["travel", "booking", "hotel", "itinerary", "trip"],
    }
    for domain, terms in weighted.items():
        if any(term in text for term in terms):
            return domain
    return "Enterprise Data Engineering"


def keywords_for_domain(domain: str) -> List[str]:
    if domain in DOMAIN_KEYWORDS:
        return DOMAIN_KEYWORDS[domain]
    for known, keywords in DOMAIN_KEYWORDS.items():
        if known.lower() in domain.lower() or domain.lower() in known.lower():
            return keywords
    return ["enterprise analytics", "data governance", "operational reporting", "data quality"]
