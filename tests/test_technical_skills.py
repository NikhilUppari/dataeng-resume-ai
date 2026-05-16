from __future__ import annotations

import unittest

from generators.technical_skills import generate_technical_skills
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

        for cloud_service in ["Glue", "Lake Formation", "Azure Data Factory", "ADLS"]:
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


def _flatten(skills):
    return [value for values in skills.values() for value in values]


if __name__ == "__main__":
    unittest.main()
