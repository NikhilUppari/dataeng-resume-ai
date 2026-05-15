from __future__ import annotations

from typing import Dict, List

from generators.technical_skills import generate_technical_skills
from parsers.jd_analyzer import JobAnalysis, all_jd_terms
from services.ats_scorer import score_resume
from services.cloud_catalog import expand_cloud_services
from services.domain_detector import keywords_for_domain
from services.timeline_validator import filter_timeline_safe, strip_timeline_unsafe_text
from utils.schema import Experience, ResumeProfile, TailoredResume
from utils.text import clamp_words, dedupe_keep_order


ACTION_VERBS = [
    "Engineered",
    "Optimized",
    "Automated",
    "Modernized",
    "Orchestrated",
    "Enhanced",
    "Delivered",
    "Configured",
    "Integrated",
    "Strengthened",
    "Refined",
    "Improved",
]


def tailor_resume(profile: ResumeProfile, jd: JobAnalysis, cloud_by_client: Dict[str, str]) -> TailoredResume:
    skills = generate_technical_skills(profile, jd, cloud_by_client)
    tailored_experiences = _tailor_experiences(profile.experiences, jd, cloud_by_client)
    summary = _generate_summary(jd, skills, tailored_experiences)
    placeholder = TailoredResume(
        summary=summary,
        technical_skills=skills,
        experiences=tailored_experiences,
        certifications=profile.certifications,
        education=profile.education,
        ats_score={},
    )
    text = render_resume_text(placeholder)
    placeholder.ats_score = score_resume(placeholder, text, jd, cloud_by_client.values())
    return placeholder


def render_resume_text(resume: TailoredResume) -> str:
    lines: List[str] = ["PROFESSIONAL SUMMARY"]
    lines.extend(f"- {item}" for item in resume.summary)
    lines.append("\nTECHNICAL SKILLS")
    for heading, values in resume.technical_skills.items():
        if values:
            lines.append(f"{heading}: {', '.join(values)}")
    lines.append("\nPROFESSIONAL EXPERIENCE")
    for exp in resume.experiences:
        lines.append(f"\nClient: {exp.client_name}")
        title_dates = " | ".join(part for part in [exp.title, exp.dates] if part)
        if title_dates:
            lines.append(title_dates)
        for bullet in exp.responsibilities:
            lines.append(f"- {bullet}")
        if exp.environment:
            lines.append(f"Environment: {', '.join(exp.environment)}")
    if resume.certifications:
        lines.append("\nCERTIFICATIONS")
        lines.extend(f"- {cert}" for cert in resume.certifications)
    if resume.education:
        lines.append("\nEDUCATION")
        lines.append(resume.education.strip())
    return "\n".join(lines).strip()


def _generate_summary(jd: JobAnalysis, skills: Dict[str, List[str]], experiences: List[Experience]) -> List[str]:
    clouds = ", ".join(skills.get("Cloud Platforms", [])[:8])
    domains = dedupe_keep_order(exp.domain for exp in experiences)
    domain_text = ", ".join(domains[:3]) if domains else "enterprise analytics"
    core_tools = ", ".join(dedupe_keep_order(jd.data_tools + jd.etl_tools + jd.databases + ["Python", "SQL", "Spark"])[:10])
    genai = ", ".join(skills.get("AI/ML & GenAI", [])[:4])
    return [
        f"Senior Data Engineer with hands-on experience delivering cloud-native data platforms across {domain_text}, using {clouds} to support reliable analytics and data products.",
        f"Strong background in {core_tools}, orchestration, data warehousing, streaming ingestion, governance, and data quality practices aligned to enterprise-scale job requirements.",
        f"Experienced translating complex business requirements into maintainable batch and streaming pipelines with clear observability, secure integrations, and measurable performance improvements.",
        f"Practical exposure to AI/ML data enablement using {genai} where relevant, while keeping solutions production-focused, compliant, and easy for analytics teams to consume.",
    ]


def _tailor_experiences(experiences: List[Experience], jd: JobAnalysis, cloud_by_client: Dict[str, str]) -> List[Experience]:
    tailored: List[Experience] = []
    total = max(len(experiences), 1)
    jd_terms = all_jd_terms(jd)
    for index, exp in enumerate(experiences):
        selected_cloud = cloud_by_client.get(exp.client_name, exp.selected_cloud or "AWS")
        cloud_tools = filter_timeline_safe(expand_cloud_services(selected_cloud, jd_terms, jd.seniority_level), exp.dates)
        domain_terms = keywords_for_domain(exp.domain)
        bullet_count = max(3, 7 - index) if total > 1 else 6
        if index == 0:
            bullet_count = max(bullet_count, 7)
        responsibilities = _generate_bullets(exp, jd, selected_cloud, cloud_tools, domain_terms, bullet_count, index)
        environment = _generate_environment(exp, jd, selected_cloud, cloud_tools, index)
        tailored.append(
            Experience(
                client_name=exp.client_name,
                title=exp.title or ("Senior Data Engineer" if index == 0 else "Data Engineer"),
                dates=exp.dates,
                domain=exp.domain,
                responsibilities=responsibilities,
                environment=environment,
                raw_text=exp.raw_text,
                selected_cloud=selected_cloud,
            )
        )
    return tailored


def _generate_bullets(
    exp: Experience,
    jd: JobAnalysis,
    cloud: str,
    cloud_tools: List[str],
    domain_terms: List[str],
    count: int,
    exp_index: int,
) -> List[str]:
    data_tools = dedupe_keep_order(jd.data_tools + jd.etl_tools + jd.databases + jd.streaming_tools + ["Python", "SQL", "Spark"])
    verbs = ACTION_VERBS[exp_index % len(ACTION_VERBS) :] + ACTION_VERBS[: exp_index % len(ACTION_VERBS)]
    patterns = [
        "{verb} {domain} data pipelines on {cloud} using {tool1}, {tool2}, and {tool3}, improving curated data availability for analytics, reporting, and downstream engineering consumers.",
        "{verb} ingestion workflows for {domain} datasets with {tool1}, {tool2}, and {tool3}, adding validation checks that reduced manual reconciliation and recurring production defects.",
        "{verb} scalable transformations in {tool1} and {tool2}, applying partitioning, schema controls, and incremental processing to improve performance for high-volume {domain} workloads.",
        "{verb} orchestration and monitoring across {tool1}, {tool2}, and {tool3}, improving pipeline recovery, alert visibility, and SLA adherence for business-critical reporting cycles.",
        "{verb} secure data integration patterns using {tool1}, {tool2}, and {tool3}, supporting governed access, audit readiness, and compliant handling of sensitive {domain} records.",
        "{verb} warehouse and lakehouse models with {tool1}, {tool2}, and SQL, enabling cleaner semantic layers for dashboards, ad hoc analytics, and recurring stakeholder reporting.",
        "{verb} streaming and batch processing patterns with {tool1}, {tool2}, and {tool3}, helping analytics teams consume fresher operational signals with stronger reliability controls.",
    ]
    bullets: List[str] = []
    tools = dedupe_keep_order(cloud_tools + data_tools)
    for idx in range(count):
        pattern = patterns[idx % len(patterns)]
        tool1 = tools[idx % len(tools)] if tools else cloud
        tool2 = tools[(idx + 3) % len(tools)] if tools else "SQL"
        tool3 = tools[(idx + 6) % len(tools)] if tools else "Python"
        domain = domain_terms[idx % len(domain_terms)] if domain_terms else "enterprise"
        text = pattern.format(
            verb=verbs[idx % len(verbs)],
            domain=domain,
            cloud=cloud,
            tool1=tool1,
            tool2=tool2,
            tool3=tool3,
        )
        bullets.append(clamp_words(strip_timeline_unsafe_text(text, exp.dates)))
    return bullets


def _generate_environment(exp: Experience, jd: JobAnalysis, cloud: str, cloud_tools: List[str], exp_index: int) -> List[str]:
    base = dedupe_keep_order(
        [cloud]
        + cloud_tools
        + jd.data_tools
        + jd.databases
        + jd.orchestration_tools
        + jd.streaming_tools
        + ["Python", "SQL", "Git", "CI/CD", "data quality"]
    )
    complexity = max(8, 18 - (exp_index * 2))
    return filter_timeline_safe(base[:complexity], exp.dates)
