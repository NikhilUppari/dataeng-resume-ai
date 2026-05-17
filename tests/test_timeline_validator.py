from __future__ import annotations

import unittest

from services.timeline_validator import earliest_year, filter_timeline_safe


class TimelineValidatorTests(unittest.TestCase):
    def test_earliest_year_reads_full_four_digit_year(self) -> None:
        self.assertEqual(earliest_year("Jan 2024 - Present"), 2024)
        self.assertEqual(earliest_year("2019 - 2021"), 2019)

    def test_new_ai_tools_are_filtered_from_older_experiences(self) -> None:
        tools = ["SageMaker", "Bedrock", "Azure OpenAI", "Gemini", "Spark"]

        self.assertEqual(filter_timeline_safe(tools, "Jan 2024 - Present"), tools)
        self.assertEqual(filter_timeline_safe(tools, "Jan 2020 - Dec 2020"), ["SageMaker", "Spark"])


if __name__ == "__main__":
    unittest.main()
