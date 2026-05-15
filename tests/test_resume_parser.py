import unittest

from parsers.resume_parser import parse_resume_text


class ResumeParserTest(unittest.TestCase):
    def test_repeated_client_labels_do_not_create_fake_experiences(self):
        resume_text = """
PROFESSIONAL EXPERIENCE
Client
CVS Health Chicago, IL
Senior Data Engineer | Jan 2024 - Present
- Built healthcare data pipelines.
Environment: Python, SQL, AWS

Client
HCA Healthcare Nashville, TN
Data Engineer | Jan 2023 - Dec 2023
- Built clinical reporting pipelines.
Environment: Python, SQL, Azure

Client
Northern Trust Chicago, IL
Data Engineer | Jan 2022 - Dec 2022
- Built banking data ingestion pipelines.
Environment: Python, SQL, Azure

eBay San Jose, CA
Data Engineer | Jan 2021 - Dec 2021
- Built seller analytics pipelines.
Environment: Python, SQL, GCP

United Airlines Chicago, IL
Data Engineer | Jan 2020 - Dec 2020
- Built flight operations reporting pipelines.
Environment: Python, SQL, Azure

MakeMyTrip Gurugram, India
Data Engineer | Jan 2019 - Dec 2019
- Built booking analytics pipelines.
Environment: Python, SQL, AWS

EDUCATION
Master of Science
"""

        profile = parse_resume_text(resume_text)

        self.assertEqual(
            [experience.client_name for experience in profile.experiences],
            [
                "CVS Health",
                "HCA Healthcare",
                "Northern Trust",
                "eBay",
                "United Airlines",
                "MakeMyTrip",
            ],
        )

    def test_only_present_known_clients_are_returned(self):
        resume_text = """
PROFESSIONAL EXPERIENCE
Client
CVS Health Chicago, IL
Senior Data Engineer | Jan 2024 - Present
- Built healthcare data pipelines.

Client
HCA Healthcare Nashville, TN
Data Engineer | Jan 2023 - Dec 2023
- Built clinical reporting pipelines.

Northern Trust Chicago, IL
Data Engineer | Jan 2022 - Dec 2022
- Built banking data ingestion pipelines.

eBay San Jose, CA
Data Engineer | Jan 2021 - Dec 2021
- Built seller analytics pipelines.

United Airlines Chicago, IL
Data Engineer | Jan 2020 - Dec 2020
- Built flight operations reporting pipelines.

EDUCATION
Master of Science
"""

        profile = parse_resume_text(resume_text)

        self.assertEqual(
            [experience.client_name for experience in profile.experiences],
            [
                "CVS Health",
                "HCA Healthcare",
                "Northern Trust",
                "eBay",
                "United Airlines",
            ],
        )


if __name__ == "__main__":
    unittest.main()
