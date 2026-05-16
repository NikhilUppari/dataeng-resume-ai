from __future__ import annotations

from typing import Dict, List


MIN_ATS_MATCH = 75.0
MIN_ADJACENT_ATS_MATCH = 55.0
MIN_TECHNICAL_MATCH = 70.0
MIN_CLOUD_ALIGNMENT = 90.0
MIN_DOMAIN_ALIGNMENT = 70.0


def evaluate_resume_quality(ats_score: Dict[str, object]) -> Dict[str, object]:
    failures: List[str] = []
    ats_match = float(ats_score.get("ats_match_percentage", 0.0))
    technical = float(ats_score.get("keyword_score", 0.0))
    cloud = float(ats_score.get("cloud_alignment_score", 0.0))
    domain = float(ats_score.get("domain_alignment_score", 0.0))
    adjacent_strategy = ats_score.get("tailoring_strategy") == "adjacent_platform_alignment"

    required_ats = MIN_ADJACENT_ATS_MATCH if adjacent_strategy else MIN_ATS_MATCH
    if ats_match < required_ats:
        failures.append(f"ATS match is below {required_ats}%.")
    if technical < MIN_TECHNICAL_MATCH:
        failures.append(f"Technical match is below {MIN_TECHNICAL_MATCH}%.")
    if cloud < MIN_CLOUD_ALIGNMENT:
        failures.append(f"Cloud alignment is below {MIN_CLOUD_ALIGNMENT}%.")
    if domain < MIN_DOMAIN_ALIGNMENT and not adjacent_strategy:
        failures.append(f"Domain alignment is below {MIN_DOMAIN_ALIGNMENT}%.")

    return {
        "passed": not failures,
        "failures": failures,
        "adjacent_platform_fit": adjacent_strategy,
        "thresholds": {
            "ats_match_percentage": required_ats,
            "keyword_score": MIN_TECHNICAL_MATCH,
            "cloud_alignment_score": MIN_CLOUD_ALIGNMENT,
            "domain_alignment_score": MIN_DOMAIN_ALIGNMENT,
        },
    }
