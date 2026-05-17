from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from parsers.jd_analyzer import JobAnalysis
from services.domain_detector import ENTERPRISE_DOMAIN, same_domain
from utils.schema import ResumeProfile
from utils.text import dedupe_keep_order


DIRECT_DOMAIN_ALIGNMENT = "direct_domain_alignment"
ADJACENT_PLATFORM_ALIGNMENT = "adjacent_platform_alignment"
LOW_ALIGNMENT = "low_alignment"
TELECOM_DOMAIN = "Telecom / Mediation / Network Platforms"

TELECOM_DIRECT_CLAIM_TERMS = [
    "ASN.1",
    "CDR",
    "UDR",
    "AMA records",
    "3GPP",
    "OSS/BSS",
    "OSS",
    "BSS",
    "Nokia",
    "Ericsson",
    "Samsung",
    "Cisco",
    "Ciena",
    "telecom mediation",
    "carrier switch",
    "charging systems",
    "mediation engines",
    "SS7",
    "SIGTRAN",
    "TAP3",
]

PLATFORM_OVERLAP_TERMS = [
    "Kafka",
    "Flink",
    "Spark Streaming",
    "Spark",
    "Kubernetes",
    "OpenShift",
    "Helm",
    "Docker",
    "Java",
    "Spring Boot",
    "Spring Kafka",
    "Spring Batch",
    "Golang",
    "Prometheus",
    "Grafana",
    "OpenTelemetry",
    "Jaeger",
    "ELK",
    "EFK",
    "Oracle",
    "SFTP",
    "REST APIs",
    "CI/CD",
]


@dataclass(frozen=True)
class TailoringStrategy:
    name: str
    job_domain: str
    matched_resume_domains: List[str] = field(default_factory=list)
    adjacent_terms: List[str] = field(default_factory=list)
    blocked_claim_terms: List[str] = field(default_factory=list)

    @property
    def has_domain_gap(self) -> bool:
        return self.name == ADJACENT_PLATFORM_ALIGNMENT


def determine_tailoring_strategy(profile: ResumeProfile, jd: JobAnalysis, job_domain: str) -> TailoringStrategy:
    resume_domains = _resume_domains(profile)
    matched_domains = [domain for domain in resume_domains if same_domain(domain, job_domain)]
    if matched_domains or not resume_domains or job_domain == ENTERPRISE_DOMAIN:
        return TailoringStrategy(
            name=DIRECT_DOMAIN_ALIGNMENT,
            job_domain=job_domain,
            matched_resume_domains=dedupe_keep_order(matched_domains or resume_domains),
        )

    adjacent_terms = _platform_overlap_terms(jd)
    if adjacent_terms:
        blocked_terms = TELECOM_DIRECT_CLAIM_TERMS if same_domain(job_domain, TELECOM_DOMAIN) else []
        return TailoringStrategy(
            name=ADJACENT_PLATFORM_ALIGNMENT,
            job_domain=job_domain,
            adjacent_terms=adjacent_terms,
            blocked_claim_terms=blocked_terms,
        )

    return TailoringStrategy(name=LOW_ALIGNMENT, job_domain=job_domain)


def filter_blocked_claim_terms(terms: Iterable[str], strategy: TailoringStrategy, source_text: str = "") -> List[str]:
    blocked = {term.lower() for term in strategy.blocked_claim_terms if term.lower() not in source_text.lower()}
    return dedupe_keep_order(term for term in terms if term.lower() not in blocked)


def _resume_domains(profile: ResumeProfile) -> List[str]:
    return dedupe_keep_order(
        exp.domain
        for exp in profile.experiences
        if exp.domain and exp.domain != ENTERPRISE_DOMAIN
    )


def _platform_overlap_terms(jd: JobAnalysis) -> List[str]:
    values = (
        jd.required_skills
        + jd.preferred_skills
        + jd.data_tools
        + jd.databases
        + jd.streaming_tools
        + jd.orchestration_tools
        + jd.etl_tools
        + jd.ats_keywords
        + jd.responsibilities
    )
    text = " ".join(values).lower()
    return dedupe_keep_order(term for term in PLATFORM_OVERLAP_TERMS if term.lower() in text)
