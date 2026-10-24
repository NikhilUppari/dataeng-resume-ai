from __future__ import annotations

import re
from typing import Dict, Iterable, List

from utils.text import dedupe_keep_order


CLOUD_SERVICES: Dict[str, List[str]] = {
    "AWS": [
        "S3",
        "Glue",
        "EMR",
        "Redshift",
        "Lambda",
        "Athena",
        "Kinesis",
        "MSK",
        "ECS",
        "EKS",
        "IAM",
        "Lake Formation",
        "CloudWatch",
        "CloudTrail",
        "Step Functions",
        "DynamoDB",
        "RDS",
        "DMS",
        "EventBridge",
        "SageMaker",
        "Bedrock",
        "QuickSight",
        "API Gateway",
        "Secrets Manager",
        "OpenSearch",
        "DataBrew",
        "CodePipeline",
        "CodeBuild",
        "Terraform",
    ],
    "Azure": [
        "Azure Data Factory",
        "ADLS",
        "Databricks",
        "Synapse",
        "Azure SQL",
        "Event Hub",
        "Stream Analytics",
        "Purview",
        "Key Vault",
        "Azure Functions",
        "Fabric",
        "Power BI",
        "Cosmos DB",
        "Azure ML",
        "Azure OpenAI",
        "Service Bus",
        "AKS",
        "Azure Monitor",
        "Logic Apps",
        "Data Explorer",
        "DevOps",
        "Bicep",
    ],
    "GCP": [
        "BigQuery",
        "Dataproc",
        "Dataflow",
        "Composer",
        "Pub/Sub",
        "Cloud Storage",
        "Vertex AI",
        "Gemini",
        "Data Fusion",
        "Datastream",
        "Cloud Functions",
        "Cloud Run",
        "GKE",
        "Bigtable",
        "Spanner",
        "Looker",
        "Cloud Monitoring",
        "Cloud Build",
        "Cloud SQL",
        "Secret Manager",
    ],
}

COMMON_DATA_STACK = [
    "Python",
    "SQL",
    "PySpark",
    "Spark",
    "Databricks",
    "Snowflake",
    "Airflow",
    "dbt",
    "Kafka",
    "Docker",
    "Kubernetes",
    "Git",
    "GitHub Actions",
    "Jenkins",
    "Terraform",
    "Great Expectations",
    "Soda",
    "Tableau",
    "Power BI",
    "REST APIs",
]


# Conservative first-available years used to prevent obviously anachronistic
# tool placement. These are intentionally kept in one table so the policy is
# easy to review and extend.
CLOUD_SERVICE_FIRST_YEAR: Dict[str, int] = {
    "Bedrock": 2023,
    "Azure OpenAI": 2023,
    "Gemini": 2023,
    "Fabric": 2023,
    "Lake Formation": 2021,
    "Vertex AI": 2021,
    "Astronomer": 2018,
    "MSK": 2018,
    "EKS": 2018,
    "AKS": 2018,
    "GKE": 2018,
    "Glue": 2017,
    "AWS Glue": 2017,
    "Athena": 2016,
    "Step Functions": 2016,
    "dbt": 2016,
}

AI_CLOUD_SERVICES = {"SageMaker", "Bedrock", "Azure ML", "Azure OpenAI", "Vertex AI", "Gemini"}


def expand_cloud_services(cloud: str, jd_terms: Iterable[str], seniority: str = "Senior") -> List[str]:
    cloud = cloud if cloud in CLOUD_SERVICES else "AWS"
    jd_lower = " ".join(jd_terms).lower()
    services = list(CLOUD_SERVICES[cloud])
    ai_focus = bool(re.search(r"\b(ai|ml|genai|llm|rag|model|feature)\b|machine learning|generative ai", jd_lower))
    if not ai_focus:
        services = [service for service in services if service not in AI_CLOUD_SERVICES]

    if "snowflake" in jd_lower:
        services.append("Snowflake")
    if "databricks" in jd_lower:
        services.append("Databricks")
    if "terraform" in jd_lower or "iac" in jd_lower:
        services.append("Terraform")
    if "quality" in jd_lower or "testing" in jd_lower:
        services.extend(["Great Expectations", "Soda"])
    if "ml" in jd_lower or "machine learning" in jd_lower:
        services.extend({"AWS": ["SageMaker"], "Azure": ["Azure ML"], "GCP": ["Vertex AI"]}[cloud])
    if "genai" in jd_lower or "generative ai" in jd_lower or "llm" in jd_lower:
        services.extend({"AWS": ["Bedrock"], "Azure": ["Azure OpenAI"], "GCP": ["Gemini"]}[cloud])

    if seniority.lower().startswith("senior"):
        services.extend(["CI/CD", "data governance", "observability", "cost optimization"])

    return dedupe_keep_order(services)


def cloud_timeline_blocklist(year_hint: int) -> List[str]:
    return [
        technology
        for technology, first_year in CLOUD_SERVICE_FIRST_YEAR.items()
        if year_hint < first_year
    ]
