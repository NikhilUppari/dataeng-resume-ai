from __future__ import annotations

import unittest
from unittest.mock import patch

from utils.pdf_exporter import build_pdf
from utils.schema import Experience, TailoredResume


class PdfExporterTests(unittest.TestCase):
    def test_build_pdf_returns_valid_pdf_bytes_without_external_converter(self) -> None:
        resume = TailoredResume(
            summary=["Built reliable streaming data platforms."],
            personal_details=["Nikhil Uppari", "nikhil@example.com | 555-123-4567"],
            technical_skills={"Streaming": ["Kafka", "Flink"], "Cloud": ["AWS"]},
            experiences=[
                Experience(
                    client_name="Example Client",
                    title="Senior Data Engineer",
                    dates="2023 - Present",
                    domain="Healthcare",
                    responsibilities=["Built Kafka pipelines with operational monitoring and data quality checks."],
                    environment=["Kafka", "Flink", "AWS"],
                )
            ],
            certifications=["AWS Certified Data Engineer"],
            education="M.S. Data Engineering",
            ats_score={},
        )

        original_import = __import__

        def block_converters(name, *args, **kwargs):
            if name in {"docx2pdf", "pypandoc"}:
                raise ImportError(name)
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=block_converters):
            pdf = build_pdf(resume)

        self.assertIsNotNone(pdf)
        self.assertTrue(pdf.startswith(b"%PDF-1.4"))
        self.assertIn(b"Nikhil Uppari", pdf)
        self.assertIn(b"Example Client", pdf)
        self.assertIn(b"Professional Experience", pdf)


if __name__ == "__main__":
    unittest.main()
