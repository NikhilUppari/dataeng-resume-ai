from __future__ import annotations

import unittest
from io import BytesIO

from docx import Document

from utils.docx_exporter import build_docx
from utils.schema import Experience, TailoredResume


class DocxExporterBoldFormattingTests(unittest.TestCase):
    def test_technical_skill_values_are_plain_while_category_labels_are_bold(self) -> None:
        document = _build_sample_document()

        skill_paragraphs = _section_paragraphs(document, "TECHNICAL SKILLS", "PROFESSIONAL EXPERIENCE")
        self.assertGreaterEqual(len(skill_paragraphs), 2)

        for paragraph in skill_paragraphs:
            self.assertEqual(paragraph.style.name, "List Bullet")
            self.assertTrue(paragraph.runs[0].bold)
            self.assertTrue(paragraph.runs[0].text.endswith(": "))

            value_runs = [run for run in paragraph.runs[1:] if run.text.strip()]
            self.assertTrue(value_runs)
            self.assertTrue(all(run.bold is not True for run in value_runs))

    def test_experience_bullets_only_bold_known_environment_technologies(self) -> None:
        document = _build_sample_document()

        bullet = _paragraph_containing(document, "patient analytics with 35% faster order pipelines")
        bold_text = _bold_text(bullet)

        self.assertIn("AWS", bold_text)
        self.assertIn("Glue", bold_text)
        self.assertIn("SQL", bold_text)
        self.assertNotIn("patient analytics", bold_text)
        self.assertNotIn("35%", bold_text)
        self.assertNotIn("order pipelines", bold_text)

    def test_environment_section_bolds_tools_but_not_business_phrases_or_metrics(self) -> None:
        document = _build_sample_document()

        environment = _paragraph_containing(document, "Environment: AWS, Glue")
        bold_runs = [run.text for run in environment.runs if run.bold is True]
        bold_text = "".join(bold_runs)

        self.assertIn("Environment: ", bold_runs)
        self.assertIn("AWS", bold_text)
        self.assertIn("Glue", bold_text)
        self.assertIn("SQL", bold_text)
        self.assertNotIn("patient analytics", bold_text)
        self.assertNotIn("35%", bold_text)
        self.assertNotIn("order pipelines", bold_text)
        self.assertNotIn("data quality", bold_text)


def _build_sample_document():
    resume = TailoredResume(
        summary=["Built governed data platforms."],
        technical_skills={
            "Cloud Platforms": ["AWS", "Glue", "patient analytics", "35%", "order pipelines"],
            "Data Engineering & ETL": ["ETL", "batch pipelines", "incremental loads"],
        },
        experiences=[
            Experience(
                client_name="Example Client",
                title="Senior Data Engineer",
                dates="2023 - Present",
                domain="Healthcare",
                responsibilities=[
                    "Built AWS Glue pipelines for patient analytics with 35% faster order pipelines and SQL checks.",
                ],
                environment=["AWS", "Glue", "patient analytics", "35%", "order pipelines", "SQL", "data quality"],
            )
        ],
        certifications=[],
        education="",
        ats_score={},
    )
    return Document(BytesIO(build_docx(resume)))


def _section_paragraphs(document, start: str, end: str):
    paragraphs = []
    in_section = False
    for paragraph in document.paragraphs:
        if paragraph.text == start:
            in_section = True
            continue
        if paragraph.text == end:
            break
        if in_section and paragraph.text:
            paragraphs.append(paragraph)
    return paragraphs


def _paragraph_containing(document, text: str):
    for paragraph in document.paragraphs:
        if text in paragraph.text:
            return paragraph
    raise AssertionError(f"Could not find paragraph containing {text!r}")


def _bold_text(paragraph) -> str:
    return "".join(run.text for run in paragraph.runs if run.bold is True)


if __name__ == "__main__":
    unittest.main()
