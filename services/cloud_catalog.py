from __future__ import annotations

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


def expand_cloud_services(cloud: str, jd_terms: Iterable[str], seniority: str = "Senior") -> List[str]:
    cloud = cloud if cloud in CLOUD_SERVICES else "AWS"
    jd_lower = " ".join(jd_terms).lower()
    services = list(CLOUD_SERVICES[cloud])

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
    blocked: List[str] = []
    if year_hint < 2023:
        blocked.extend(["Bedrock", "Azure OpenAI", "Gemini"])
    if year_hint < 2023:
        blocked.append("Fabric")
    if year_hint < 2021:
        blocked.extend(["Lake Formation", "Vertex AI"])
    return blocked
