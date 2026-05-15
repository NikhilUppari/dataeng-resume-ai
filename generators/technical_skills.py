from __future__ import annotations

from typing import Dict, Iterable, List

from parsers.jd_analyzer import JobAnalysis, all_jd_terms
from services.cloud_catalog import COMMON_DATA_STACK, expand_cloud_services
from utils.schema import ResumeProfile
from utils.text import dedupe_keep_order


def generate_technical_skills(profile: ResumeProfile, jd: JobAnalysis, cloud_by_client: Dict[str, str]) -> Dict[str, List[str]]:
    selected_clouds = dedupe_keep_order(cloud_by_client.values())
    cloud_services: List[str] = []
    jd_terms = all_jd_terms(jd)
    for cloud in selected_clouds:
        cloud_services.extend(expand_cloud_services(cloud, jd_terms, jd.seniority_level))

    existing = []
    for skills in profile.technical_skills.values():
        existing.extend(skills)

    return {
        "Cloud Platforms": dedupe_keep_order(selected_clouds + cloud_services),
        "Big Data Technologies": dedupe_keep_order(jd.data_tools + ["Spark", "PySpark", "Databricks", "Delta Lake", "Hive"]),
        "Data Engineering & ETL": dedupe_keep_order(jd.etl_tools + ["ETL", "ELT", "batch pipelines", "incremental loads", "data lakehouse"]),
        "Data Warehousing": dedupe_keep_order(["Snowflake", "Redshift", "BigQuery", "Synapse", "dimensional modeling", "star schema"] + jd.databases),
        "Databases": dedupe_keep_order(jd.databases + ["PostgreSQL", "SQL Server", "Oracle", "NoSQL"]),
        "Streaming & Messaging": dedupe_keep_order(jd.streaming_tools + ["Kafka", "Kinesis", "Pub/Sub", "Event Hub"]),
        "Programming Languages": dedupe_keep_order(["Python", "SQL", "PySpark", "Scala", "Shell scripting"]),
        "Orchestration": dedupe_keep_order(jd.orchestration_tools + ["Airflow", "Step Functions", "Composer", "Azure Data Factory"]),
        "DevOps & CI/CD": dedupe_keep_order(["Git", "GitHub Actions", "Jenkins", "Docker", "Kubernetes", "Terraform"]),
        "Data Governance & Security": dedupe_keep_order(["data quality", "data lineage", "PII", "IAM", "Key Vault", "Secrets Manager", "audit controls"]),
        "AI/ML & GenAI": dedupe_keep_order(jd.ai_ml_tools + _genai_terms_if_relevant(jd_terms)),
        "APIs & Integration": dedupe_keep_order(["REST APIs", "API Gateway", "event-driven integration", "file ingestion", "CDC"]),
        "BI & Visualization": dedupe_keep_order(["Power BI", "Tableau", "QuickSight", "Looker"]),
        "Monitoring & Observability": dedupe_keep_order(["CloudWatch", "Azure Monitor", "Cloud Monitoring", "logging", "alerting", "SLA monitoring"]),
        "Testing & Data Quality": dedupe_keep_order(["Great Expectations", "Soda", "unit testing", "reconciliation checks", "schema validation"]),
        "Additional ATS Keywords": dedupe_keep_order(existing + jd.required_skills + jd.preferred_skills + jd.ats_keywords + COMMON_DATA_STACK)[:40],
    }


def _genai_terms_if_relevant(jd_terms: Iterable[str]) -> List[str]:
    joined = " ".join(jd_terms).lower()
    if any(term in joined for term in ["genai", "generative ai", "llm", "bedrock", "openai", "gemini"]):
        return ["LLM integration", "RAG pipelines", "vector search", "prompt evaluation"]
    return ["MLflow", "feature engineering"]
