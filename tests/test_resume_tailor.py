from __future__ import annotations

import unittest

from generators.resume_tailor import render_resume_text, tailor_resume
from services.ats_scorer import score_resume
from services.domain_detector import infer_job_domain
from services.resume_quality_gate import evaluate_resume_quality
from utils.schema import Experience, JobAnalysis, ResumeProfile
from utils.technology_terms import extract_known_technologies


class ResumeTailoringDomainTests(unittest.TestCase):
    def test_professional_summary_changes_for_different_jds(self) -> None:
        profile = ResumeProfile(
            raw_text="Built healthcare data platforms.",
            experiences=[
                Experience(client_name="Confidential Client", dates="Jan 2024 - Present", domain="Healthcare", environment=["Python", "SQL"])
            ],
        )
        healthcare_jd = JobAnalysis(
            required_skills=["FHIR", "HL7"],
            data_tools=["Databricks"],
            databases=["Snowflake"],
            domain_keywords=["HIPAA", "patient analytics"],
            responsibilities=["Build clinical reporting pipelines for patient analytics teams."],
            seniority_level="Senior",
        )
        finance_jd = JobAnalysis(
            required_skills=["Kafka", "Terraform"],
            data_tools=["Spark"],
            databases=["Redshift"],
            domain_keywords=["AML", "KYC", "fraud detection"],
            responsibilities=["Build fraud monitoring pipelines for banking risk teams."],
            seniority_level="Senior",
        )

        healthcare = tailor_resume(profile, healthcare_jd, {"Confidential Client": "AWS"})
        finance = tailor_resume(profile, finance_jd, {"Confidential Client": "AWS"})

        self.assertNotEqual(healthcare.summary, finance.summary)
        self.assertIn("FHIR", " ".join(healthcare.summary))
        self.assertIn("fraud monitoring", " ".join(finance.summary))

    def test_same_domain_clients_receive_distinct_domain_responsibilities(self) -> None:
        profile = ResumeProfile(
            raw_text="Oak Street Health and HCA Healthcare data engineering experience.",
            experiences=[
                Experience(client_name="Oak Street Health", title="Senior Data Engineer", dates="Jan 2024 - Present", domain="Healthcare"),
                Experience(client_name="HCA Healthcare", title="Data Engineer", dates="Jan 2023 - Dec 2023", domain="Healthcare"),
            ],
        )
        jd = JobAnalysis(
            data_tools=["Spark", "Databricks"],
            databases=["Snowflake"],
            etl_tools=["AWS Glue"],
            domain_keywords=["HIPAA", "PHI", "FHIR", "claims data", "patient analytics"],
            seniority_level="Senior",
        )

        tailored = tailor_resume(profile, jd, {"Oak Street Health": "AWS", "HCA Healthcare": "AWS"})
        first, second = tailored.experiences
        rendered = render_resume_text(tailored)

        self.assertEqual(first.domain, "Healthcare")
        self.assertEqual(second.domain, "Healthcare")
        self.assertNotEqual(first.responsibilities, second.responsibilities)
        self.assertNotEqual(first.responsibilities[0], second.responsibilities[0])

        for expected in ["HIPAA", "PHI", "FHIR", "claims data", "patient analytics"]:
            self.assertIn(expected, rendered)
        self.assertNotIn("reliably reliably", rendered)

    def test_generated_responsibility_points_follow_word_and_technology_targets(self) -> None:
        profile = ResumeProfile(
            raw_text="Built healthcare data platforms.",
            experiences=[
                Experience(client_name="Oak Street Health", dates="Jan 2024 - Present", domain="Healthcare", environment=["Python", "SQL"])
            ],
        )
        jd = JobAnalysis(
            data_tools=["Databricks", "Spark"],
            databases=["Snowflake"],
            streaming_tools=["Kafka"],
            orchestration_tools=["Airflow"],
            domain_keywords=["HIPAA", "patient analytics"],
            seniority_level="Senior",
        )

        tailored = tailor_resume(profile, jd, {"Oak Street Health": "AWS"})
        tool_terms = tailored.experiences[0].environment

        for point in tailored.experiences[0].responsibilities:
            matches = extract_known_technologies(point, tool_terms)
            self.assertGreaterEqual(len(matches), 3, point)
            self.assertLessEqual(len(matches), 4, point)
            self.assertGreaterEqual(len(point.rstrip(".").split()), 29, point)
            self.assertLessEqual(len(point.rstrip(".").split()), 33, point)

    def test_client_responsibility_counts_follow_format_branch_targets(self) -> None:
        clients = [
            ("Oak Street Health", "Healthcare"),
            ("Northern Trust", "Financial Services / Banking / Wealth Management / Asset Servicing"),
            ("United Airlines", "Aviation"),
            ("eBay", "Retail / E-commerce"),
            ("MakeMyTrip", "Travel / Online Travel Platform"),
            ("Confidential Client", "Enterprise Data Engineering"),
        ]
        profile = ResumeProfile(
            raw_text="Multiple client data engineering history.",
            experiences=[
                Experience(client_name=client, dates="Jan 2021 - Present", domain=domain, environment=["Python", "SQL"])
                for client, domain in clients
            ],
        )
        jd = JobAnalysis(
            data_tools=["Databricks", "Spark"],
            databases=["Snowflake"],
            streaming_tools=["Kafka"],
            orchestration_tools=["Airflow"],
            domain_keywords=["analytics platforms"],
            seniority_level="Senior",
        )

        tailored = tailor_resume(profile, jd, {client: "AWS" for client, _ in clients})

        self.assertEqual([len(exp.responsibilities) for exp in tailored.experiences], [27, 25, 23, 20, 10, 10])

    def test_rendered_resume_text_uses_docx_aligned_section_and_client_format(self) -> None:
        resume = tailor_resume(
            ResumeProfile(
                raw_text="Built healthcare data platforms.",
                personal_details=["Nikhil Uppari", "nikhil@example.com | 555-123-4567"],
                experiences=[
                    Experience(
                        client_name="Oak Street Health",
                        title="Senior Data Engineer",
                        dates="Jan 2024 - Present",
                        domain="Healthcare",
                        environment=["Python", "SQL"],
                    )
                ],
                certifications=["AWS Certified Data Engineer"],
                education="M.S. Data Engineering",
            ),
            JobAnalysis(
                data_tools=["Databricks", "Spark"],
                databases=["Snowflake"],
                domain_keywords=["HIPAA", "patient analytics"],
                seniority_level="Senior",
            ),
            {"Oak Street Health": "AWS"},
        )

        rendered = render_resume_text(resume)

        self.assertTrue(rendered.startswith("Nikhil Uppari\nnikhil@example.com | 555-123-4567"))
        self.assertIn("Professional Summary", rendered)
        self.assertIn("Technical Skills", rendered)
        self.assertIn("Professional Experience", rendered)
        self.assertIn("Certifications", rendered)
        self.assertIn("Education", rendered)
        self.assertIn(
            "Oak Street Health | Senior Data Engineer | Jan 2024 - Present | Healthcare",
            rendered,
        )
        self.assertNotIn("Client: Oak Street Health", rendered)
        self.assertNotIn("PROFESSIONAL EXPERIENCE", rendered)
        self.assertNotIn("\nSenior Data Engineer | Jan 2024 - Present\n", rendered)

    def test_professional_summary_has_twelve_points(self) -> None:
        profile = ResumeProfile(
            raw_text="Built healthcare data platforms.",
            experiences=[
                Experience(client_name="Oak Street Health", dates="Jan 2024 - Present", domain="Healthcare", environment=["Python", "SQL"])
            ],
        )
        jd = JobAnalysis(
            data_tools=["Databricks", "Spark"],
            databases=["Snowflake"],
            streaming_tools=["Kafka"],
            domain_keywords=["HIPAA", "patient analytics"],
            seniority_level="Senior",
        )

        tailored = tailor_resume(profile, jd, {"Oak Street Health": "AWS"})

        self.assertEqual(len(tailored.summary), 12)

    def test_recent_client_gets_timeline_safe_ai_enablement(self) -> None:
        profile = ResumeProfile(
            raw_text="Built healthcare data platforms.",
            experiences=[
                Experience(client_name="Oak Street Health", dates="Jan 2024 - Present", domain="Healthcare", environment=["Python", "SQL"]),
                Experience(client_name="HCA Healthcare", dates="Jan 2020 - Dec 2020", domain="Healthcare", environment=["Python", "SQL"]),
            ],
        )
        jd = JobAnalysis(
            data_tools=["Databricks", "Spark"],
            databases=["Snowflake"],
            streaming_tools=["Kafka"],
            domain_keywords=["HIPAA", "patient analytics"],
            seniority_level="Senior",
        )

        tailored = tailor_resume(profile, jd, {"Oak Street Health": "AWS", "HCA Healthcare": "AWS"})
        recent_text = "\n".join(tailored.experiences[0].responsibilities) + "\n" + ", ".join(tailored.experiences[0].environment)
        older_text = "\n".join(tailored.experiences[1].responsibilities) + "\n" + ", ".join(tailored.experiences[1].environment)

        self.assertIn("SageMaker", recent_text)
        self.assertIn("Bedrock", recent_text)
        self.assertNotIn("Bedrock", older_text)

    def test_generic_experience_does_not_claim_unmatched_jd_domain(self) -> None:
        profile = ResumeProfile(
            raw_text="Built enterprise data platforms.",
            experiences=[
                Experience(
                    client_name="Confidential Client",
                    title="Data Engineer",
                    dates="Jan 2022 - Dec 2023",
                    domain="Enterprise Data Engineering",
                )
            ],
        )
        jd = JobAnalysis(
            data_tools=["Spark"],
            databases=["Snowflake"],
            orchestration_tools=["Airflow"],
            domain_keywords=["AML", "KYC", "fraud detection", "risk analytics"],
            responsibilities=["Build regulatory reporting pipelines for banking risk teams."],
            seniority_level="Senior",
        )

        tailored = tailor_resume(profile, jd, {"Confidential Client": "Azure"})
        rendered = render_resume_text(tailored)

        self.assertEqual(tailored.experiences[0].domain, "Enterprise Data Engineering")
        self.assertEqual(tailored.ats_score["tailoring_strategy"], "adjacent_platform_alignment")
        for unsupported_domain_claim in ["AML", "KYC", "fraud detection", "risk analytics"]:
            self.assertNotIn(unsupported_domain_claim, rendered)

    def test_missing_jd_domain_terms_do_not_penalize_domain_alignment(self) -> None:
        jd = JobAnalysis(data_tools=["Spark"])
        ats = score_resume(None, "Built Spark pipelines on AWS.", jd, ["AWS"])

        self.assertEqual(ats["domain_alignment_score"], 100.0)
        self.assertEqual(ats["domain_missing"], [])

    def test_ats_guidance_groups_priority_gaps_and_score_ratings(self) -> None:
        jd = JobAnalysis(
            data_tools=["Spark", "Databricks"],
            databases=["Snowflake"],
            streaming_tools=["Kafka"],
            domain_keywords=["HIPAA", "claims data"],
        )

        ats = score_resume(
            None,
            "Built Spark pipelines on AWS for HIPAA reporting.",
            jd,
            ["AWS", "Azure"],
        )

        self.assertIn("score_breakdown", ats)
        self.assertEqual(ats["score_breakdown"]["technical"], "Weak")
        self.assertEqual(ats["score_breakdown"]["cloud"], "Needs work")
        self.assertEqual(ats["score_breakdown"]["domain"], "Needs work")
        self.assertIn("priority_gaps", ats)
        self.assertIn("Databricks", ats["priority_gaps"]["technical_tools"])
        self.assertIn("Snowflake", ats["priority_gaps"]["technical_tools"])
        self.assertIn("Kafka", ats["priority_gaps"]["technical_tools"])
        self.assertIn("claims data", ats["priority_gaps"]["domain_terms"])
        self.assertIn("Azure", ats["priority_gaps"]["cloud_terms"])
        self.assertTrue(any("most recent three experiences" in suggestion for suggestion in ats["suggestions"]))

    def test_ats_missing_tools_only_include_known_technologies(self) -> None:
        jd = JobAnalysis(
            data_tools=["Databricks"],
            responsibilities=["Build reliable pipelines for analytics partners."],
        )

        ats = score_resume(None, "Built Python pipelines.", jd, ["AWS"])

        self.assertIn("Databricks", ats["missing_tools"])
        self.assertNotIn("Build reliable pipelines for analytics partners.", ats["missing_tools"])

    def test_quality_gate_passes_only_when_alignment_thresholds_are_met(self) -> None:
        weak = {
            "ats_match_percentage": 65.0,
            "keyword_score": 60.0,
            "cloud_alignment_score": 100.0,
            "domain_alignment_score": 80.0,
        }
        strong = {
            "ats_match_percentage": 85.0,
            "keyword_score": 75.0,
            "cloud_alignment_score": 100.0,
            "domain_alignment_score": 90.0,
        }
        adjacent = {
            "ats_match_percentage": 58.0,
            "keyword_score": 72.0,
            "cloud_alignment_score": 100.0,
            "domain_alignment_score": 20.0,
            "tailoring_strategy": "adjacent_platform_alignment",
        }

        self.assertFalse(evaluate_resume_quality(weak)["passed"])
        self.assertTrue(evaluate_resume_quality(strong)["passed"])
        self.assertTrue(evaluate_resume_quality(adjacent)["passed"])

    def test_alignment_repair_pass_adds_remaining_gap_terms(self) -> None:
        profile = ResumeProfile(
            raw_text="Built healthcare data platforms.",
            experiences=[
                Experience(client_name="Oak Street Health", dates="Jan 2024 - Present", domain="Healthcare", environment=["Python", "SQL"])
            ],
        )
        jd = JobAnalysis(
            data_tools=["Databricks"],
            databases=["Snowflake"],
            streaming_tools=["Kafka"],
            orchestration_tools=["Airflow"],
            domain_keywords=["HIPAA", "claims data"],
            responsibilities=["Build data observability for claims teams."],
            seniority_level="Senior",
        )

        repaired = tailor_resume(profile, jd, {"Oak Street Health": "AWS"}, alignment_pass=1)
        rendered = render_resume_text(repaired)

        for expected in ["Databricks", "Snowflake", "Kafka", "Airflow", "HIPAA", "claims data"]:
            self.assertIn(expected, rendered)

    def test_older_experiences_use_partial_jd_tools_and_strong_cloud_context(self) -> None:
        profile = ResumeProfile(
            raw_text="Multiple client data engineering history.",
            experiences=[
                Experience(client_name="Oak Street Health", dates="Jan 2024 - Present", domain="Healthcare", environment=["Python", "SQL"]),
                Experience(client_name="Northern Trust", dates="Jan 2023 - Dec 2023", domain="Financial Services / Banking / Wealth Management / Asset Servicing", environment=["Python", "SQL"]),
                Experience(client_name="United Airlines", dates="Jan 2022 - Dec 2022", domain="Aviation", environment=["Python", "SQL"]),
                Experience(client_name="eBay", dates="Jan 2021 - Dec 2021", domain="Retail / E-commerce", environment=["Python", "SQL"]),
            ],
        )
        jd = JobAnalysis(
            data_tools=["Databricks", "dbt"],
            databases=["Snowflake"],
            streaming_tools=["Kafka"],
            domain_keywords=["patient analytics"],
            seniority_level="Senior",
        )

        tailored = tailor_resume(
            profile,
            jd,
            {
                "Oak Street Health": "AWS",
                "Northern Trust": "AWS",
                "United Airlines": "AWS",
                "eBay": "AWS",
            },
        )
        recent_text = "\n".join(
            "\n".join(exp.responsibilities) + "\n" + ", ".join(exp.environment)
            for exp in tailored.experiences[:3]
        )
        older = tailored.experiences[3]
        older_text = "\n".join(older.responsibilities) + "\n" + ", ".join(older.environment)
        jd_tools = ["Databricks", "dbt", "Snowflake", "Kafka"]

        for jd_tool in jd_tools:
            self.assertIn(jd_tool, recent_text)

        older_jd_tool_matches = [tool for tool in jd_tools if tool in older_text]
        self.assertEqual(len(older_jd_tool_matches), 2)

        self.assertIn("seller analytics", older_text)
        self.assertIn("inventory optimization", older_text)
        for cloud_tool in ["S3", "Glue", "EMR", "Redshift", "Kinesis", "MSK"]:
            self.assertIn(cloud_tool, older_text)

    def test_telecom_jd_without_telecom_client_uses_adjacent_platform_positioning(self) -> None:
        profile = ResumeProfile(
            raw_text="Healthcare, banking, retail, and aviation data engineering background.",
            experiences=[
                Experience(client_name="CVS Health", dates="Jan 2024 - Present", domain="Healthcare", environment=["Python", "SQL", "Kafka"]),
                Experience(client_name="Northern Trust", dates="Jan 2023 - Dec 2023", domain="Financial Services / Banking / Wealth Management / Asset Servicing", environment=["Spark", "Airflow"]),
                Experience(client_name="eBay", dates="Jan 2022 - Dec 2022", domain="Retail / E-commerce", environment=["Kubernetes", "Docker"]),
            ],
        )
        jd = JobAnalysis(
            required_skills=["Java", "Spring Boot", "Spring Kafka", "Golang", "ASN.1", "CDR", "OSS/BSS", "Nokia", "Ericsson"],
            data_tools=["Spark"],
            databases=["Oracle"],
            streaming_tools=["Kafka", "Flink"],
            orchestration_tools=["Kubernetes", "OpenShift", "Helm"],
            domain_keywords=["telecom", "telecom mediation", "ASN.1", "CDR", "UDR", "3GPP", "OSS/BSS", "Nokia", "Ericsson"],
            responsibilities=["Build telecom mediation systems for CDR and UDR processing using ASN.1 decoding."],
            seniority_level="Senior",
        )

        self.assertEqual(infer_job_domain(jd), "Telecom / Mediation / Network Platforms")

        tailored = tailor_resume(profile, jd, {"CVS Health": "AWS", "Northern Trust": "AWS", "eBay": "AWS"})
        rendered = render_resume_text(tailored)

        self.assertEqual(tailored.ats_score["tailoring_strategy"], "adjacent_platform_alignment")
        self.assertIn("No direct telecom client experience detected", tailored.ats_score["domain_gap_warning"])
        for expected in ["Kafka", "Flink", "Kubernetes", "OpenShift", "Prometheus", "Grafana"]:
            self.assertIn(expected, rendered)
        for blocked in ["Nokia", "Ericsson", "ASN.1", "CDR", "UDR", "OSS/BSS", "3GPP"]:
            self.assertNotIn(blocked, rendered)
        self.assertIn("streaming and platform engineering", " ".join(tailored.summary))
        self.assertIn("telecom-style operational event workloads", " ".join(tailored.summary))

    def test_telecom_alignment_repair_does_not_inject_direct_mediation_claims(self) -> None:
        profile = ResumeProfile(
            raw_text="Healthcare, finance, and retail data engineering background with Kafka platforms.",
            experiences=[
                Experience(client_name="CVS Health", dates="Jan 2024 - Present", domain="Healthcare", environment=["Python", "SQL", "Kafka"]),
                Experience(client_name="Northern Trust", dates="Jan 2023 - Dec 2023", domain="Financial Services / Banking / Wealth Management / Asset Servicing", environment=["Spark", "Airflow"]),
            ],
        )
        jd = JobAnalysis(
            required_skills=["Java", "Spring Boot", "Spring Kafka", "Golang", "ASN.1", "CDR", "UDR", "OSS/BSS"],
            databases=["Oracle"],
            streaming_tools=["Kafka", "Flink"],
            orchestration_tools=["Kubernetes", "OpenShift", "Helm"],
            domain_keywords=["telecom", "telecom mediation", "ASN.1", "CDR", "UDR", "3GPP", "OSS/BSS"],
            responsibilities=["Build telecom mediation systems for CDR and UDR processing using ASN.1 decoding."],
            seniority_level="Senior",
        )

        repaired = tailor_resume(profile, jd, {"CVS Health": "AWS", "Northern Trust": "AWS"}, alignment_pass=1)
        rendered = render_resume_text(repaired)

        self.assertEqual(repaired.ats_score["tailoring_strategy"], "adjacent_platform_alignment")
        for blocked in ["ASN.1", "CDR", "UDR", "OSS/BSS", "3GPP"]:
            self.assertNotIn(blocked, rendered)
        self.assertNotIn("Build telecom mediation systems", rendered)


if __name__ == "__main__":
    unittest.main()
