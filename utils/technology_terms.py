from __future__ import annotations

import re
from typing import Iterable, List

from parsers.jd_analyzer import TECH_GROUPS
from services.cloud_catalog import CLOUD_SERVICES, COMMON_DATA_STACK
from utils.text import dedupe_keep_order


def _normalize_tool(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


NON_TOOL_PHRASES = {
    "audit controls",
    "batch pipelines",
    "cost optimization",
    "data governance",
    "data lakehouse",
    "data lineage",
    "data quality",
    "dimensional modeling",
    "event-driven integration",
    "feature engineering",
    "file ingestion",
    "incremental loads",
    "logging",
    "observability",
    "order pipelines",
    "patient analytics",
    "prompt evaluation",
    "reconciliation checks",
    "risk analytics",
    "schema validation",
    "sla monitoring",
    "star schema",
    "unit testing",
}

SHORT_TOOL_ALLOWLIST = {
    "ADF",
    "AKS",
    "AWS",
    "dbt",
    "DMS",
    "ECS",
    "EKS",
    "ELT",
    "EMR",
    "ETL",
    "GCP",
    "GKE",
    "IAM",
    "MSK",
    "RDS",
    "S3",
    "SQL",
}
SHORT_TOOL_ALLOWLIST_NORMALIZED = {_normalize_tool(term) for term in SHORT_TOOL_ALLOWLIST}

EXTRA_TECH_TERMS = {
    "ADLS",
    "Amazon Kinesis",
    "Amazon MSK",
    "Amazon Redshift",
    "Amazon S3",
    "Amazon SageMaker",
    "Apache Airflow",
    "Apache Kafka",
    "Apache Spark",
    "Azure DevOps",
    "Bicep",
    "CDC",
    "CI/CD",
    "CloudWatch",
    "Databricks SQL",
    "Delta Lake",
    "Docker",
    "GitHub Actions",
    "Google Cloud",
    "Informatica PowerCenter",
    "Java",
    "KMS",
    "Kubernetes",
    "Linux",
    "MWAA",
    "NoSQL",
    "NumPy",
    "Pandas",
    "PL/SQL",
    "RBAC",
    "REST API",
    "REST APIs",
    "Scala",
    "Shell Scripting",
    "Spark MLlib",
    "Spark SQL",
    "Spark Structured Streaming",
    "SSIS",
    "Talend",
    "Unix Shell Scripting",
    "Unity Catalog",
}


def is_known_technology(value: str) -> bool:
    normalized = _normalize_tool(value)
    if not normalized or normalized in NON_TOOL_PHRASES:
        return False
    if looks_like_metric(value):
        return False
    if len(value.strip()) <= 3 and normalized not in SHORT_TOOL_ALLOWLIST_NORMALIZED:
        return False
    return normalized in KNOWN_TECH_TERMS


def extract_known_technologies(text: str, candidates: Iterable[str] | None = None) -> List[str]:
    if not text:
        return []

    terms = list(candidates or KNOWN_TECH_DISPLAY)
    matches = []
    for term in sorted(terms, key=len, reverse=True):
        if not is_known_technology(term):
            continue
        for match in iter_tool_matches(text, term):
            start, end = match.span()
            if not any(start < existing_end and end > existing_start for existing_start, existing_end, _ in matches):
                matches.append((start, end, term))
            break

    matches.sort(key=lambda item: item[0])
    return dedupe_keep_order(term for _, _, term in matches)


def iter_tool_matches(text: str, tool: str) -> Iterable[re.Match[str]]:
    escaped = re.escape(tool.strip())
    if not escaped:
        return []
    pattern = rf"(?<![A-Za-z0-9+#./-]){escaped}(?![A-Za-z0-9+#./-])"
    return re.finditer(pattern, text, flags=re.IGNORECASE)


def looks_like_metric(value: str) -> bool:
    stripped = value.strip()
    return bool(re.fullmatch(r"[$+-]?\d[\d,]*(?:\.\d+)?\s*(?:%|x|k|m|b|tb|gb|ms|s|sec|secs|seconds|minutes|hours)?", stripped, flags=re.IGNORECASE))


_KNOWN_TECH_SOURCE = (
    COMMON_DATA_STACK
    + [term for terms in CLOUD_SERVICES.values() for term in terms]
    + [term for terms in TECH_GROUPS.values() for term in terms]
    + list(EXTRA_TECH_TERMS)
)

KNOWN_TECH_DISPLAY = dedupe_keep_order(_KNOWN_TECH_SOURCE)
KNOWN_TECH_TERMS = frozenset(_normalize_tool(term) for term in KNOWN_TECH_DISPLAY)
