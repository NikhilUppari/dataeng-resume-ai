from __future__ import annotations

from typing import Dict, Iterable, List

from parsers.jd_analyzer import JobAnalysis, all_jd_terms
from services.cloud_catalog import COMMON_DATA_STACK, CLOUD_SERVICES, expand_cloud_services
from utils.schema import Experience, ResumeProfile
from utils.technology_terms import extract_known_technologies, is_known_technology
from utils.text import dedupe_keep_order


def generate_technical_skills(
    profile: ResumeProfile,
    jd: JobAnalysis,
    cloud_by_client: Dict[str, str],
    tailored_experiences: Iterable[Experience] | None = None,
) -> Dict[str, List[str]]:
    selected_clouds = dedupe_keep_order(cloud for cloud in cloud_by_client.values() if cloud)
    cloud_services: List[str] = []
    jd_terms = all_jd_terms(jd)
    for cloud in selected_clouds:
        cloud_services.extend(expand_cloud_services(cloud, jd_terms, jd.seniority_level))

    existing_tools = _existing_tools(profile)
    experience_tools = _experience_tools(list(profile.experiences) + list(tailored_experiences or []))
    jd_tools = _jd_tools(jd)
    role_tools = dedupe_keep_order(
        tool
        for tool in jd_tools + cloud_services + experience_tools + existing_tools + COMMON_DATA_STACK
        if is_known_technology(tool)
    )

    return {
        "Cloud Platforms": _limit(dedupe_keep_order(selected_clouds + jd.cloud_platforms + _matching_tools(role_tools, _cloud_terms())), 60),
        "Big Data Technologies": _limit(dedupe_keep_order(jd.data_tools + _matching_tools(role_tools, _BIG_DATA_TOOLS))),
        "Data Engineering & ETL": _limit(dedupe_keep_order(jd.etl_tools + _matching_tools(role_tools, _ETL_TOOLS) + ["ETL", "ELT"])),
        "Data Warehousing": _limit(dedupe_keep_order(_matching_tools(jd_tools + role_tools, _WAREHOUSE_TOOLS) + ["dimensional modeling", "star schema"])),
        "Databases": _limit(dedupe_keep_order(jd.databases + _matching_tools(role_tools, _DATABASE_TOOLS))),
        "Streaming & Messaging": _limit(dedupe_keep_order(jd.streaming_tools + _matching_tools(role_tools, _STREAMING_TOOLS))),
        "Programming Languages": _limit(dedupe_keep_order(_matching_tools(role_tools, _PROGRAMMING_TOOLS) + ["Python", "SQL"])),
        "Orchestration": _limit(dedupe_keep_order(jd.orchestration_tools + _matching_tools(role_tools, _ORCHESTRATION_TOOLS))),
        "DevOps & CI/CD": _limit(dedupe_keep_order(_matching_tools(role_tools, _DEVOPS_TOOLS))),
        "Data Governance & Security": _limit(dedupe_keep_order(_matching_tools(role_tools, _GOVERNANCE_TOOLS) + ["data quality", "data lineage", "PII", "audit controls"])),
        "AI/ML & GenAI": _limit(dedupe_keep_order(jd.ai_ml_tools + _matching_tools(role_tools, _AI_ML_TOOLS) + _genai_terms_if_relevant(jd_terms))),
        "APIs & Integration": _limit(dedupe_keep_order(_matching_tools(role_tools, _API_TOOLS) + ["REST APIs", "CDC", "event-driven integration"])),
        "BI & Visualization": _limit(dedupe_keep_order(_matching_tools(role_tools, _BI_TOOLS))),
        "Monitoring & Observability": _limit(dedupe_keep_order(_matching_tools(role_tools, _MONITORING_TOOLS) + ["logging", "alerting", "SLA monitoring"])),
        "Testing & Data Quality": _limit(dedupe_keep_order(_matching_tools(role_tools, _TESTING_TOOLS) + ["unit testing", "reconciliation checks", "schema validation"])),
        "Additional ATS Keywords": _additional_keywords(role_tools, jd),
    }


def _genai_terms_if_relevant(jd_terms: Iterable[str]) -> List[str]:
    joined = " ".join(jd_terms).lower()
    if any(term in joined for term in ["genai", "generative ai", "llm", "bedrock", "openai", "gemini"]):
        return ["LLM integration", "RAG pipelines", "vector search", "prompt evaluation"]
    return ["MLflow", "feature engineering"]


def _jd_tools(jd: JobAnalysis) -> List[str]:
    direct = (
        jd.cloud_platforms
        + jd.data_tools
        + jd.databases
        + jd.orchestration_tools
        + jd.etl_tools
        + jd.streaming_tools
        + jd.ai_ml_tools
        + jd.required_skills
        + jd.preferred_skills
        + jd.ats_keywords
    )
    tools = [tool for tool in direct if is_known_technology(tool)]
    tools.extend(extract_known_technologies(" ".join(direct)))
    return dedupe_keep_order(tools)


def _existing_tools(profile: ResumeProfile) -> List[str]:
    values: List[str] = []
    for skills in profile.technical_skills.values():
        values.extend(skills)
    values.extend(extract_known_technologies(profile.raw_text))
    return dedupe_keep_order(value for value in values if is_known_technology(value))


def _experience_tools(experiences: Iterable[Experience]) -> List[str]:
    tools: List[str] = []
    for exp in experiences:
        tools.extend(tool for tool in exp.environment if is_known_technology(tool))
        tools.extend(extract_known_technologies(" ".join(exp.responsibilities)))
    return dedupe_keep_order(tools)


def _matching_tools(values: Iterable[str], allowed: Iterable[str]) -> List[str]:
    allowed_lookup = {value.lower() for value in allowed}
    return dedupe_keep_order(value for value in values if value.lower() in allowed_lookup)


def _cloud_terms() -> List[str]:
    terms: List[str] = []
    for cloud, services in CLOUD_SERVICES.items():
        terms.append(cloud)
        terms.extend(services)
    terms.extend(["Google Cloud", "Amazon S3", "Amazon Redshift", "Amazon Kinesis", "Amazon MSK", "Amazon SageMaker"])
    return dedupe_keep_order(terms)


def _additional_keywords(role_tools: List[str], jd: JobAnalysis) -> List[str]:
    grouped_terms = set(
        term.lower()
        for terms in [
            _cloud_terms(),
            _BIG_DATA_TOOLS,
            _ETL_TOOLS,
            _WAREHOUSE_TOOLS,
            _DATABASE_TOOLS,
            _STREAMING_TOOLS,
            _PROGRAMMING_TOOLS,
            _ORCHESTRATION_TOOLS,
            _DEVOPS_TOOLS,
            _GOVERNANCE_TOOLS,
            _AI_ML_TOOLS,
            _API_TOOLS,
            _BI_TOOLS,
            _MONITORING_TOOLS,
            _TESTING_TOOLS,
        ]
        for term in terms
    )
    jd_terms = [term for term in jd.required_skills + jd.preferred_skills + jd.ats_keywords if is_known_technology(term)]
    remaining_tools = [tool for tool in role_tools if tool.lower() not in grouped_terms]
    return _limit(dedupe_keep_order(remaining_tools + jd_terms), 30)


def _limit(values: Iterable[str], maximum: int = 24) -> List[str]:
    return list(values)[:maximum]


_BIG_DATA_TOOLS = [
    "Spark",
    "PySpark",
    "Databricks",
    "Delta Lake",
    "Hive",
    "Hadoop",
    "Iceberg",
    "dbt",
    "Apache Spark",
]

_ETL_TOOLS = [
    "AWS Glue",
    "Glue",
    "Azure Data Factory",
    "ADF",
    "Dataflow",
    "Data Fusion",
    "Informatica",
    "Informatica PowerCenter",
    "Talend",
    "SSIS",
    "Fivetran",
    "Matillion",
]

_WAREHOUSE_TOOLS = ["Snowflake", "Redshift", "Amazon Redshift", "BigQuery", "Synapse", "Databricks SQL", "SQL Server"]
_DATABASE_TOOLS = ["PostgreSQL", "SQL Server", "MySQL", "Oracle", "DynamoDB", "Cosmos DB", "BigQuery", "Redshift", "Snowflake", "Teradata", "MongoDB", "NoSQL", "RDS", "Spanner", "Bigtable", "Cloud SQL"]
_STREAMING_TOOLS = ["Kafka", "Apache Kafka", "Kinesis", "Amazon Kinesis", "Pub/Sub", "Event Hub", "Spark Streaming", "Spark Structured Streaming", "Flink", "MSK", "Amazon MSK", "Stream Analytics"]
_PROGRAMMING_TOOLS = ["Python", "SQL", "PySpark", "Scala", "Java", "PL/SQL", "Shell Scripting", "Unix Shell Scripting"]
_ORCHESTRATION_TOOLS = ["Airflow", "Apache Airflow", "Composer", "Control-M", "Autosys", "Step Functions", "ADF", "Azure Data Factory", "Prefect", "Dagster", "MWAA"]
_DEVOPS_TOOLS = ["Git", "GitHub Actions", "Jenkins", "Docker", "Kubernetes", "Terraform", "CI/CD", "CodePipeline", "CodeBuild", "Cloud Build", "Azure DevOps", "DevOps", "Bicep", "ECS", "EKS", "AKS", "GKE"]
_GOVERNANCE_TOOLS = ["Unity Catalog", "Purview", "Lake Formation", "IAM", "KMS", "Key Vault", "Secrets Manager", "Secret Manager", "CloudTrail", "RBAC"]
_AI_ML_TOOLS = ["SageMaker", "Amazon SageMaker", "Bedrock", "Vertex AI", "Azure ML", "Azure OpenAI", "Gemini", "MLflow", "scikit-learn", "Spark MLlib", "Pandas", "NumPy"]
_API_TOOLS = ["REST API", "REST APIs", "API Gateway", "Service Bus", "Logic Apps", "EventBridge", "CDC"]
_BI_TOOLS = ["Power BI", "Tableau", "QuickSight", "Looker"]
_MONITORING_TOOLS = ["CloudWatch", "Azure Monitor", "Cloud Monitoring", "OpenSearch"]
_TESTING_TOOLS = ["Great Expectations", "Soda"]
