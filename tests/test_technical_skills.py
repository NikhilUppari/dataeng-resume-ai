from __future__ import annotations

import unittest

from generators.technical_skills import generate_technical_skills
from services.tailoring_strategy import ADJACENT_PLATFORM_ALIGNMENT, TELECOM_DOMAIN, TailoringStrategy
from utils.schema import Experience, JobAnalysis, ResumeProfile


class TechnicalSkillsGenerationTests(unittest.TestCase):
    def test_skills_include_jd_tools_selected_cloud_services_and_experience_tools(self) -> None:
        profile = ResumeProfile(
            raw_text="Built healthcare analytics with Snowflake, Airflow, and patient analytics.",
            technical_skills={"Existing": ["Snowflake", "patient analytics"]},
            experiences=[
                Experience(
                    client_name="Acme Health",
                    responsibilities=["Modeled Databricks SQL tables with Unity Catalog governance."],
                    environment=["Databricks SQL", "Unity Catalog"],
                )
            ],
        )
        jd = JobAnalysis(
            data_tools=["Databricks", "Spark"],
            databases=["Snowflake"],
            etl_tools=["AWS Glue"],
            streaming_tools=["Kafka"],
            orchestration_tools=["Airflow"],
            required_skills=["Terraform", "Docker", "patient analytics"],
            ats_keywords=["Power BI", "risk analytics"],
            seniority_level="Senior",
        )
        tailored = [
            Experience(
                client_name="Acme Health",
                responsibilities=["Engineered AWS Glue and Azure Data Factory pipelines with Kafka."],
                environment=["AWS", "Glue", "Azure Data Factory", "Kafka", "Terraform"],
            )
        ]

        skills = generate_technical_skills(profile, jd, {"Acme Health": "AWS", "RetailCo": "Azure"}, tailored)
        flattened = _flatten(skills)

        for expected in ["AWS Glue", "Databricks", "Spark", "Snowflake", "Kafka", "Airflow", "Terraform", "Docker", "Power BI"]:
            self.assertIn(expected, flattened)

        for cloud_service in ["Glue", "Lake Formation", "Azure Data Factory"]:
            self.assertIn(cloud_service, flattened)

        self.assertIn("Unity Catalog", skills["Data Governance & Security"])
        self.assertIn("Databricks SQL", skills["Data Warehousing"])
        self.assertNotIn("patient analytics", flattened)
        self.assertNotIn("risk analytics", flattened)

    def test_selected_clouds_drive_multi_cloud_skill_depth_without_jd_cloud_terms(self) -> None:
        profile = ResumeProfile(raw_text="")
        jd = JobAnalysis(seniority_level="Senior")

        skills = generate_technical_skills(profile, jd, {"A": "GCP", "B": "Azure"})

        self.assertIn("GCP", skills["Cloud Platforms"])
        self.assertIn("Azure", skills["Cloud Platforms"])
        self.assertIn("BigQuery", skills["Cloud Platforms"])
        self.assertIn("Azure Data Factory", skills["Cloud Platforms"])
        self.assertIn("Composer", skills["Orchestration"])
        self.assertIn("Power BI", skills["BI & Visualization"])

    def test_generated_skill_categories_stay_compact(self) -> None:
        profile = ResumeProfile(
            raw_text="Built platforms with AWS, Azure, GCP, Spark, Kafka, Airflow, Docker, Kubernetes, Terraform, Power BI.",
            technical_skills={
                "Existing": [
                    "Spark",
                    "PySpark",
                    "Databricks",
                    "Hadoop",
                    "Hive",
                    "dbt",
                    "Delta Lake",
                    "Iceberg",
                    "Kafka",
                    "Flink",
                    "Airflow",
                    "Terraform",
                    "Docker",
                    "Kubernetes",
                    "Power BI",
                ]
            },
        )
        jd = JobAnalysis(
            cloud_platforms=["AWS", "Azure", "GCP"],
            data_tools=["Spark", "PySpark", "Databricks", "Hadoop", "Hive", "dbt", "Delta Lake", "Iceberg"],
            databases=["Snowflake", "Redshift", "BigQuery", "Oracle", "PostgreSQL", "SQL Server"],
            streaming_tools=["Kafka", "Flink", "Spark Streaming", "MSK", "Kinesis", "Pub/Sub"],
            orchestration_tools=["Airflow", "Control-M", "Autosys", "Step Functions"],
            required_skills=["Terraform", "Docker", "Kubernetes", "Jenkins", "Great Expectations", "Power BI"],
            seniority_level="Senior",
        )

        skills = generate_technical_skills(profile, jd, {"A": "AWS", "B": "Azure", "C": "GCP"})

        self.assertLessEqual(len(skills["Cloud Platforms"]), 28)
        for category, values in skills.items():
            if category == "Cloud Platforms":
                continue
            expected_limit = 18 if category == "Additional ATS Keywords" else 16
            self.assertLessEqual(len(values), expected_limit)

    def test_adjacent_telecom_strategy_keeps_skills_streaming_platform_focused(self) -> None:
        profile = ResumeProfile(raw_text="Healthcare and finance streaming platforms.")
        jd = JobAnalysis(
            required_skills=["Java", "Spring Boot", "Spring Kafka", "Golang", "ASN.1", "CDR"],
            databases=["Oracle"],
            streaming_tools=["Kafka", "Flink"],
            orchestration_tools=["Kubernetes", "OpenShift", "Helm"],
            domain_keywords=["telecom", "CDR", "ASN.1"],
            seniority_level="Senior",
        )
        strategy = TailoringStrategy(
            name=ADJACENT_PLATFORM_ALIGNMENT,
            job_domain=TELECOM_DOMAIN,
            adjacent_terms=["Kafka", "Flink", "Kubernetes", "OpenShift", "Helm", "Java", "Spring Boot", "Golang"],
            blocked_claim_terms=["ASN.1", "CDR"],
        )

        skills = generate_technical_skills(profile, jd, {"A": "AWS"}, tailoring_strategy=strategy)
        flattened = _flatten(skills)

        self.assertIn("Streaming & Distributed Systems", skills)
        self.assertIn("Backend & Platform Engineering", skills)
        self.assertIn("Observability & SRE", skills)
        for expected in ["Kafka", "Flink", "Spring Boot", "Kubernetes", "OpenShift", "Helm", "Oracle"]:
            self.assertIn(expected, flattened)
        self.assertNotIn("ASN.1", flattened)
        self.assertNotIn("CDR", flattened)
        self.assertNotIn("AI/ML & GenAI", skills)


def _flatten(skills):
    return [value for values in skills.values() for value in values]


if __name__ == "__main__":
    unittest.main()
