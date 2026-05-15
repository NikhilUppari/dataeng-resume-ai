from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Experience:
    client_name: str
    title: str = ""
    dates: str = ""
    domain: str = ""
    responsibilities: List[str] = field(default_factory=list)
    environment: List[str] = field(default_factory=list)
    raw_text: str = ""
    selected_cloud: str = "AWS"


@dataclass
class ResumeProfile:
    raw_text: str
    professional_summary: str = ""
    technical_skills: Dict[str, List[str]] = field(default_factory=dict)
    experiences: List[Experience] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    education: str = ""
    sections: Dict[str, str] = field(default_factory=dict)


@dataclass
class JobAnalysis:
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    cloud_platforms: List[str] = field(default_factory=list)
    data_tools: List[str] = field(default_factory=list)
    databases: List[str] = field(default_factory=list)
    orchestration_tools: List[str] = field(default_factory=list)
    etl_tools: List[str] = field(default_factory=list)
    streaming_tools: List[str] = field(default_factory=list)
    ai_ml_tools: List[str] = field(default_factory=list)
    domain_keywords: List[str] = field(default_factory=list)
    ats_keywords: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    seniority_level: str = "Senior"


@dataclass
class TailoredResume:
    summary: List[str]
    technical_skills: Dict[str, List[str]]
    experiences: List[Experience]
    certifications: List[str]
    education: str
    ats_score: Dict[str, object]
