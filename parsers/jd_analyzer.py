from __future__ import annotations

import re
from typing import Dict, Iterable, List

from utils.schema import JobAnalysis
from utils.text import dedupe_keep_order


TECH_GROUPS: Dict[str, List[str]] = {
    "cloud_platforms": ["AWS", "Azure", "GCP", "Google Cloud", "Databricks", "Snowflake"],
    "data_tools": ["Spark", "PySpark", "Databricks", "Hadoop", "Hive", "dbt", "Delta Lake", "Iceberg"],
    "databases": ["SQL Server", "PostgreSQL", "MySQL", "Oracle", "DynamoDB", "Cosmos DB", "BigQuery", "Redshift", "Snowflake", "Teradata", "MongoDB"],
    "orchestration_tools": ["Airflow", "Composer", "Control-M", "Autosys", "Step Functions", "ADF", "Azure Data Factory", "Prefect", "Dagster"],
    "etl_tools": ["Informatica", "Talend", "SSIS", "AWS Glue", "Azure Data Factory", "Dataflow", "Data Fusion", "Fivetran", "Matillion"],
    "streaming_tools": ["Kafka", "Kinesis", "Pub/Sub", "Event Hub", "Spark Streaming", "Flink", "MSK", "Stream Analytics"],
    "ai_ml_tools": ["SageMaker", "Bedrock", "Vertex AI", "Azure ML", "Azure OpenAI", "Gemini", "MLflow", "scikit-learn"],
    "certifications": ["AWS Certified", "Azure Data Engineer", "Google Professional Data Engineer", "Databricks Certified", "SnowPro"],
}

DOMAIN_TERMS = [
    "HIPAA",
    "PHI",
    "FHIR",
    "HL7",
    "PCI-DSS",
    "SOX",
    "AML",
    "KYC",
    "fraud",
    "risk",
    "claims",
    "patient",
    "inventory",
    "flight",
    "booking",
]

RESPONSIBILITY_VERBS = [
    "build",
    "develop",
    "design",
    "optimize",
    "migrate",
    "automate",
    "ingest",
    "model",
    "orchestrate",
    "monitor",
    "validate",
    "govern",
]


def analyze_jd(jd_text: str) -> JobAnalysis:
    jd_text = jd_text or ""
    analysis = JobAnalysis()
    for field, terms in TECH_GROUPS.items():
        found = _find_terms(jd_text, terms)
        setattr(analysis, field, found)

    analysis.domain_keywords = _find_terms(jd_text, DOMAIN_TERMS)
    analysis.responsibilities = _extract_responsibility_lines(jd_text)
    analysis.seniority_level = _detect_seniority(jd_text)
    analysis.required_skills = _extract_skills_after_labels(jd_text, ["required", "must have", "qualifications"])
    analysis.preferred_skills = _extract_skills_after_labels(jd_text, ["preferred", "nice to have", "bonus"])

    ats_candidates = []
    for value in analysis.__dict__.values():
        if isinstance(value, list):
            ats_candidates.extend(value)
    ats_candidates.extend(_capitalized_tech_phrases(jd_text))
    analysis.ats_keywords = dedupe_keep_order(ats_candidates)
    return analysis


def all_jd_terms(analysis: JobAnalysis) -> List[str]:
    terms: List[str] = []
    for value in analysis.__dict__.values():
        if isinstance(value, list):
            terms.extend(value)
    return dedupe_keep_order(terms)


def _find_terms(text: str, terms: Iterable[str]) -> List[str]:
    lower = text.lower()
    return dedupe_keep_order(term for term in terms if term.lower() in lower)


def _extract_responsibility_lines(text: str) -> List[str]:
    lines = []
    for line in text.splitlines():
        clean = line.strip("-*• ")
        if len(clean.split()) >= 5 and any(verb in clean.lower() for verb in RESPONSIBILITY_VERBS):
            lines.append(clean)
    return dedupe_keep_order(lines)[:12]


def _detect_seniority(text: str) -> str:
    lower = text.lower()
    if "principal" in lower:
        return "Principal"
    if "lead" in lower:
        return "Senior"
    if "senior" in lower or "sr." in lower:
        return "Senior"
    if "mid" in lower:
        return "Mid-level"
    return "Senior"


def _extract_skills_after_labels(text: str, labels: Iterable[str]) -> List[str]:
    results: List[str] = []
    for label in labels:
        pattern = rf"(?is){re.escape(label)}[^:\n]*[:\n](.+?)(?:\n\s*\n|preferred|required|responsibilities|qualifications|$)"
        for match in re.finditer(pattern, text):
            results.extend(_capitalized_tech_phrases(match.group(1)))
    return dedupe_keep_order(results)[:30]


def _capitalized_tech_phrases(text: str) -> List[str]:
    known = []
    for terms in TECH_GROUPS.values():
        known.extend(terms)
    known.extend([
        "Python",
        "SQL",
        "Scala",
        "Java",
        "CI/CD",
        "Terraform",
        "Docker",
        "Kubernetes",
        "GitHub Actions",
        "Jenkins",
        "REST API",
        "Great Expectations",
        "Data Quality",
        "Data Governance",
        "Data Lake",
        "Data Warehouse",
    ])
    return _find_terms(text, known)
