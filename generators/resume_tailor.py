from __future__ import annotations

from typing import Dict, List

from generators.technical_skills import generate_technical_skills
from parsers.jd_analyzer import JobAnalysis, all_jd_terms
from services.ats_scorer import score_resume
from services.cloud_catalog import expand_cloud_services
from services.domain_detector import infer_job_domain, is_enterprise_domain, keywords_for_domain, same_domain
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

JD_TAILORED_EXPERIENCE_COUNT = 3
BASELINE_DATA_STACK = ["Python", "SQL", "Spark", "Airflow", "Git", "data quality"]


def tailor_resume(profile: ResumeProfile, jd: JobAnalysis, cloud_by_client: Dict[str, str], alignment_pass: int = 0) -> TailoredResume:
    job_domain = infer_job_domain(jd)
    tailored_experiences = _tailor_experiences(profile.experiences, jd, cloud_by_client, job_domain)
    skills = generate_technical_skills(profile, jd, cloud_by_client, tailored_experiences)
    summary = _generate_summary(jd, skills, tailored_experiences, job_domain)
    placeholder = TailoredResume(
        summary=summary,
        technical_skills=skills,
        experiences=tailored_experiences,
        certifications=profile.certifications,
        education=profile.education,
        ats_score={},
    )
    if alignment_pass > 0:
        _apply_alignment_repair(placeholder, jd, cloud_by_client, alignment_pass)
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


def _generate_summary(jd: JobAnalysis, skills: Dict[str, List[str]], experiences: List[Experience], job_domain: str) -> List[str]:
    clouds = ", ".join(skills.get("Cloud Platforms", [])[:8])
    domains = dedupe_keep_order([job_domain] + [exp.domain for exp in experiences])
    domain_text = ", ".join(domains[:3]) if domains else "enterprise analytics"
    domain_keywords = ", ".join(jd.domain_keywords[:6]) if jd.domain_keywords else domain_text
    core_tools = ", ".join(_summary_tools(jd))
    cloud_focus = ", ".join(dedupe_keep_order(jd.cloud_platforms + skills.get("Cloud Platforms", [])[:5])[:6])
    responsibility_focus = _summary_responsibility_focus(jd)
    seniority = jd.seniority_level or "Senior"
    genai = ", ".join(skills.get("AI/ML & GenAI", [])[:4])
    return [
        f"{seniority} Data Engineer tailored for {domain_text} roles, using {cloud_focus or clouds} with {core_tools} to deliver JD-aligned data platforms and analytics products.",
        f"Strong match for {domain_keywords} requirements, with hands-on delivery across orchestration, data warehousing, streaming ingestion, governance, and data quality controls.",
        f"Experienced with {responsibility_focus}, translating job-specific business needs into maintainable pipelines, trusted datasets, and measurable reporting outcomes.",
        f"Practical exposure to AI/ML data enablement using {genai} where relevant, while keeping solutions production-focused, compliant, observable, and easy for analytics teams to consume.",
    ]


def _summary_tools(jd: JobAnalysis) -> List[str]:
    tools = dedupe_keep_order(
        jd.required_skills
        + jd.data_tools
        + jd.etl_tools
        + jd.databases
        + jd.streaming_tools
        + jd.orchestration_tools
        + ["Python", "SQL", "Spark"]
    )
    return tools[:10]


def _summary_responsibility_focus(jd: JobAnalysis) -> str:
    terms = dedupe_keep_order(jd.responsibilities + jd.preferred_skills + jd.ats_keywords)
    for term in terms:
        words = term.split()
        if 3 <= len(words) <= 14:
            return term.rstrip(".")
    fallback = dedupe_keep_order(jd.data_tools + jd.etl_tools + jd.databases + jd.streaming_tools)
    if fallback:
        return "building " + ", ".join(fallback[:5]) + " solutions"
    return "building batch and streaming data products"


def _tailor_experiences(experiences: List[Experience], jd: JobAnalysis, cloud_by_client: Dict[str, str], job_domain: str) -> List[Experience]:
    tailored: List[Experience] = []
    total = max(len(experiences), 1)
    jd_terms = all_jd_terms(jd)
    for index, exp in enumerate(experiences):
        tailor_to_jd = index < JD_TAILORED_EXPERIENCE_COUNT
        selected_cloud = cloud_by_client.get(exp.client_name, exp.selected_cloud or "AWS")
        cloud_context_terms = jd_terms if tailor_to_jd else []
        cloud_tools = filter_timeline_safe(expand_cloud_services(selected_cloud, cloud_context_terms, jd.seniority_level), exp.dates)
        active_domain = _resolve_experience_domain(exp.domain, job_domain)
        domain_terms = _terms_for_experience_domain(active_domain, jd, job_domain, tailor_to_jd)
        bullet_count = max(3, 7 - index) if total > 1 else 6
        if index == 0:
            bullet_count = max(bullet_count, 7)
        responsibilities = _generate_bullets(exp, jd, selected_cloud, cloud_tools, active_domain, domain_terms, bullet_count, index, tailor_to_jd)
        environment = _generate_environment(exp, jd, selected_cloud, cloud_tools, index, tailor_to_jd)
        tailored.append(
            Experience(
                client_name=exp.client_name,
                title=exp.title or ("Senior Data Engineer" if index == 0 else "Data Engineer"),
                dates=exp.dates,
                domain=active_domain,
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
    active_domain: str,
    domain_terms: List[str],
    count: int,
    exp_index: int,
    tailor_to_jd: bool,
) -> List[str]:
    data_tools = _tools_for_experience(exp, jd, tailor_to_jd, exp_index)
    verbs = ACTION_VERBS[exp_index % len(ACTION_VERBS) :] + ACTION_VERBS[: exp_index % len(ACTION_VERBS)]
    patterns = _patterns_for_domain(active_domain)
    focus = _focus_for_experience(active_domain, exp.client_name, exp_index)
    bullets: List[str] = []
    if tailor_to_jd:
        tools = dedupe_keep_order(data_tools + cloud_tools)
    else:
        tools = dedupe_keep_order(cloud_tools + data_tools)
    for idx in range(count):
        pattern = patterns[idx % len(patterns)]
        tool1 = tools[idx % len(tools)] if tools else cloud
        tool2 = tools[(idx + 3) % len(tools)] if tools else "SQL"
        tool3 = tools[(idx + 6) % len(tools)] if tools else "Python"
        tool4 = tools[(idx + 9) % len(tools)] if tools else "Airflow"
        domain = domain_terms[(idx + _stable_offset(exp.client_name, exp_index)) % len(domain_terms)] if domain_terms else "enterprise"
        focus_area = focus[idx % len(focus)]
        text = pattern.format(
            verb=verbs[idx % len(verbs)],
            domain=domain,
            focus=focus_area["focus"],
            data_asset=focus_area["data_asset"],
            stakeholder=focus_area["stakeholder"],
            control=focus_area["control"],
            outcome=focus_area["outcome"],
            cloud=cloud,
            tool1=tool1,
            tool2=tool2,
            tool3=tool3,
        )
        text = _ensure_tool_mentions(text, [tool1, tool2, tool3, tool4])
        bullets.append(clamp_words(strip_timeline_unsafe_text(text, exp.dates)))
    return bullets


def _generate_environment(exp: Experience, jd: JobAnalysis, cloud: str, cloud_tools: List[str], exp_index: int, tailor_to_jd: bool) -> List[str]:
    if tailor_to_jd:
        base = dedupe_keep_order(
            [cloud]
            + jd.data_tools
            + jd.databases
            + jd.orchestration_tools
            + jd.streaming_tools
            + ["Python", "SQL", "Git", "CI/CD", "data quality"]
            + cloud_tools
        )
    else:
        jd_subset = _jd_tool_subset_for_older_experience(jd, exp.client_name, exp_index)
        base = dedupe_keep_order([cloud] + jd_subset + cloud_tools + exp.environment + BASELINE_DATA_STACK)
    complexity = 24
    return filter_timeline_safe(base[:complexity], exp.dates)


def _resolve_experience_domain(exp_domain: str, job_domain: str) -> str:
    if is_enterprise_domain(exp_domain) and not is_enterprise_domain(job_domain):
        return job_domain
    return exp_domain or job_domain


def _terms_for_experience_domain(exp_domain: str, jd: JobAnalysis, job_domain: str, tailor_to_jd: bool) -> List[str]:
    terms = keywords_for_domain(exp_domain)
    if tailor_to_jd and same_domain(exp_domain, job_domain):
        terms = jd.domain_keywords + terms
    return dedupe_keep_order(terms)


def _tools_for_experience(exp: Experience, jd: JobAnalysis, tailor_to_jd: bool, exp_index: int) -> List[str]:
    if tailor_to_jd:
        return dedupe_keep_order(
            jd.data_tools
            + jd.etl_tools
            + jd.databases
            + jd.streaming_tools
            + jd.orchestration_tools
            + ["Python", "SQL", "Spark"]
        )
    return dedupe_keep_order(_jd_tool_subset_for_older_experience(jd, exp.client_name, exp_index) + exp.environment + BASELINE_DATA_STACK)


def _jd_tool_subset_for_older_experience(jd: JobAnalysis, client_name: str, exp_index: int) -> List[str]:
    jd_tools = dedupe_keep_order(
        jd.data_tools
        + jd.etl_tools
        + jd.databases
        + jd.streaming_tools
        + jd.orchestration_tools
    )
    if not jd_tools:
        return []
    target_count = max(1, len(jd_tools) // 2)
    offset = _stable_offset(client_name, exp_index) % len(jd_tools)
    rotated = jd_tools[offset:] + jd_tools[:offset]
    return rotated[:target_count]


def _ensure_tool_mentions(text: str, tools: List[str]) -> str:
    unique_tools = dedupe_keep_order(tool for tool in tools if tool)
    if not unique_tools:
        return text
    lower = text.lower()
    present = [tool for tool in unique_tools if tool.lower() in lower]
    missing = [tool for tool in unique_tools if tool.lower() not in lower]
    needed = max(0, min(4, len(unique_tools)) - len(present))
    if needed == 0 or not missing:
        return text
    additions = missing[:needed]
    return text.rstrip(".") + f", with {', '.join(additions)} supporting validation, monitoring, and operational handoff."


def _patterns_for_domain(domain: str) -> List[str]:
    if same_domain(domain, "Healthcare"):
        return [
            "{verb} {focus} pipelines for {data_asset} on {cloud} using {tool1}, {tool2}, and {tool3}, improving {outcome} for {stakeholder} teams.",
            "{verb} {domain} workflows with {tool1}, {tool2}, and {tool3}, adding {control} checks for safer clinical reporting and compliant analytics delivery.",
            "{verb} curated models for {data_asset} in {tool1} and {tool2}, improving patient analytics, provider analytics, and trusted operational reporting.",
            "{verb} orchestration and monitoring across {tool1}, {tool2}, and {tool3}, strengthening SLA recovery for {focus} and regulated healthcare reporting cycles.",
            "{verb} secure integration patterns for {domain} records using {tool1}, {tool2}, and {tool3}, supporting HIPAA, PHI handling, audit readiness, and governed access.",
            "{verb} warehouse and lakehouse layers for {data_asset} with {tool1}, {tool2}, and SQL, enabling cleaner dashboards for {stakeholder} users.",
            "{verb} batch and streaming patterns with {tool1}, {tool2}, and {tool3}, helping teams consume fresher healthcare compliance and clinical operations signals.",
        ]
    if same_domain(domain, "Financial Services / Banking / Wealth Management / Asset Servicing"):
        return [
            "{verb} {focus} pipelines for {data_asset} on {cloud} using {tool1}, {tool2}, and {tool3}, improving {outcome} for {stakeholder} teams.",
            "{verb} {domain} workflows with {tool1}, {tool2}, and {tool3}, adding {control} controls for audit-ready regulatory reporting and reconciliation.",
            "{verb} curated models for {data_asset} in {tool1} and {tool2}, improving risk analytics, fraud detection, and transaction processing visibility.",
            "{verb} orchestration and monitoring across {tool1}, {tool2}, and {tool3}, strengthening SLA recovery for {focus} and business-critical finance reporting.",
            "{verb} secure integration patterns for {domain} records using {tool1}, {tool2}, and {tool3}, supporting SOX, PCI-DSS, AML, KYC, and governed access.",
            "{verb} warehouse and lakehouse layers for {data_asset} with {tool1}, {tool2}, and SQL, enabling cleaner dashboards for {stakeholder} users.",
            "{verb} batch and streaming patterns with {tool1}, {tool2}, and {tool3}, helping teams consume fresher regulatory, fraud, and risk signals.",
        ]
    if same_domain(domain, "Retail / E-commerce"):
        return [
            "{verb} {focus} pipelines for {data_asset} on {cloud} using {tool1}, {tool2}, and {tool3}, improving {outcome} for {stakeholder} teams.",
            "{verb} {domain} workflows with {tool1}, {tool2}, and {tool3}, adding {control} checks for cleaner order pipelines and customer analytics.",
            "{verb} curated models for {data_asset} in {tool1} and {tool2}, improving inventory optimization, pricing analytics, and seller analytics reporting.",
            "{verb} orchestration and monitoring across {tool1}, {tool2}, and {tool3}, strengthening SLA recovery for {focus} and digital commerce reporting.",
            "{verb} secure integration patterns for {domain} datasets using {tool1}, {tool2}, and {tool3}, supporting governed access and reliable supply chain analytics.",
            "{verb} warehouse and lakehouse layers for {data_asset} with {tool1}, {tool2}, and SQL, enabling cleaner dashboards for {stakeholder} users.",
            "{verb} batch and streaming patterns with {tool1}, {tool2}, and {tool3}, helping teams consume fresher inventory, order, and recommendation signals.",
        ]
    if same_domain(domain, "Aviation"):
        return [
            "{verb} {focus} pipelines for {data_asset} on {cloud} using {tool1}, {tool2}, and {tool3}, improving {outcome} for {stakeholder} teams.",
            "{verb} {domain} workflows with {tool1}, {tool2}, and {tool3}, adding {control} checks for cleaner safety reporting and airline operations analytics.",
            "{verb} curated models for {data_asset} in {tool1} and {tool2}, improving flight operations, crew scheduling, and passenger analytics reporting.",
            "{verb} orchestration and monitoring across {tool1}, {tool2}, and {tool3}, strengthening SLA recovery for {focus} and operational reporting cycles.",
            "{verb} secure integration patterns for {domain} datasets using {tool1}, {tool2}, and {tool3}, supporting governed access and route optimization analytics.",
            "{verb} warehouse and lakehouse layers for {data_asset} with {tool1}, {tool2}, and SQL, enabling cleaner dashboards for {stakeholder} users.",
            "{verb} batch and streaming patterns with {tool1}, {tool2}, and {tool3}, helping teams consume fresher flight, maintenance, and loyalty analytics signals.",
        ]
    if same_domain(domain, "Travel / Online Travel Platform"):
        return [
            "{verb} {focus} pipelines for {data_asset} on {cloud} using {tool1}, {tool2}, and {tool3}, improving {outcome} for {stakeholder} teams.",
            "{verb} {domain} workflows with {tool1}, {tool2}, and {tool3}, adding {control} checks for cleaner booking analytics and cancellation analytics.",
            "{verb} curated models for {data_asset} in {tool1} and {tool2}, improving itinerary data, pricing trends, and customer segmentation reporting.",
            "{verb} orchestration and monitoring across {tool1}, {tool2}, and {tool3}, strengthening SLA recovery for {focus} and online travel reporting cycles.",
            "{verb} secure integration patterns for {domain} datasets using {tool1}, {tool2}, and {tool3}, supporting governed access and recommendation systems.",
            "{verb} warehouse and lakehouse layers for {data_asset} with {tool1}, {tool2}, and SQL, enabling cleaner dashboards for {stakeholder} users.",
            "{verb} batch and streaming patterns with {tool1}, {tool2}, and {tool3}, helping teams consume fresher hotel, flight search, and pricing signals.",
        ]
    return [
        "{verb} {focus} pipelines for {data_asset} on {cloud} using {tool1}, {tool2}, and {tool3}, improving {outcome} for {stakeholder} teams.",
        "{verb} ingestion workflows for {domain} datasets with {tool1}, {tool2}, and {tool3}, adding {control} checks that reduced recurring production defects.",
        "{verb} scalable transformations in {tool1} and {tool2}, applying partitioning, schema controls, and incremental processing for high-volume {domain} workloads.",
        "{verb} orchestration and monitoring across {tool1}, {tool2}, and {tool3}, improving pipeline recovery, alert visibility, and SLA adherence.",
        "{verb} secure data integration patterns using {tool1}, {tool2}, and {tool3}, supporting governed access, audit readiness, and compliant data handling.",
        "{verb} warehouse and lakehouse models with {tool1}, {tool2}, and SQL, enabling cleaner semantic layers for dashboards and stakeholder reporting.",
        "{verb} streaming and batch processing patterns with {tool1}, {tool2}, and {tool3}, helping analytics teams consume fresher operational signals.",
    ]


def _focus_for_experience(domain: str, client_name: str, exp_index: int) -> List[Dict[str, str]]:
    focus = _focus_library(domain)
    offset = exp_index % len(focus)
    return focus[offset:] + focus[:offset]


def _focus_library(domain: str) -> List[Dict[str, str]]:
    if same_domain(domain, "Healthcare"):
        return [
            {"focus": "patient access", "data_asset": "FHIR and HL7 feeds", "stakeholder": "care management", "control": "PHI validation", "outcome": "clinical reporting trust"},
            {"focus": "claims modernization", "data_asset": "claims data", "stakeholder": "payer operations", "control": "HIPAA lineage", "outcome": "claims analytics reliability"},
            {"focus": "provider performance", "data_asset": "provider analytics marts", "stakeholder": "population health", "control": "quality reconciliation", "outcome": "care gap reporting"},
            {"focus": "pharmacy analytics", "data_asset": "pharmacy data", "stakeholder": "clinical analytics", "control": "sensitive data masking", "outcome": "medication trend visibility"},
        ]
    if same_domain(domain, "Financial Services / Banking / Wealth Management / Asset Servicing"):
        return [
            {"focus": "risk reporting", "data_asset": "risk analytics marts", "stakeholder": "risk management", "control": "SOX reconciliation", "outcome": "regulatory reporting trust"},
            {"focus": "fraud monitoring", "data_asset": "transaction processing feeds", "stakeholder": "fraud operations", "control": "AML exception", "outcome": "fraud detection coverage"},
            {"focus": "client holdings", "data_asset": "wealth management datasets", "stakeholder": "asset servicing", "control": "KYC validation", "outcome": "advisor reporting accuracy"},
            {"focus": "audit modernization", "data_asset": "audit controls evidence", "stakeholder": "compliance", "control": "PCI-DSS lineage", "outcome": "audit readiness"},
        ]
    if same_domain(domain, "Retail / E-commerce"):
        return [
            {"focus": "seller analytics", "data_asset": "marketplace event feeds", "stakeholder": "seller operations", "control": "schema validation", "outcome": "seller analytics reliability"},
            {"focus": "inventory optimization", "data_asset": "inventory and order pipelines", "stakeholder": "supply chain", "control": "stock reconciliation", "outcome": "inventory visibility"},
            {"focus": "pricing analytics", "data_asset": "pricing trend datasets", "stakeholder": "merchandising", "control": "price anomaly", "outcome": "margin reporting trust"},
            {"focus": "customer analytics", "data_asset": "recommendation systems features", "stakeholder": "growth analytics", "control": "event completeness", "outcome": "customer segmentation depth"},
        ]
    if same_domain(domain, "Aviation"):
        return [
            {"focus": "flight operations", "data_asset": "flight operations feeds", "stakeholder": "operations control", "control": "schedule reconciliation", "outcome": "route optimization visibility"},
            {"focus": "crew scheduling", "data_asset": "crew scheduling datasets", "stakeholder": "workforce planning", "control": "duty rule validation", "outcome": "crew analytics reliability"},
            {"focus": "maintenance analytics", "data_asset": "aircraft maintenance data", "stakeholder": "maintenance planning", "control": "safety reporting", "outcome": "maintenance reporting trust"},
            {"focus": "loyalty analytics", "data_asset": "passenger analytics marts", "stakeholder": "commercial analytics", "control": "identity matching", "outcome": "loyalty trend visibility"},
        ]
    if same_domain(domain, "Travel / Online Travel Platform"):
        return [
            {"focus": "booking analytics", "data_asset": "booking event feeds", "stakeholder": "travel operations", "control": "reservation reconciliation", "outcome": "booking funnel visibility"},
            {"focus": "itinerary intelligence", "data_asset": "itinerary data", "stakeholder": "customer experience", "control": "trip state validation", "outcome": "itinerary reporting reliability"},
            {"focus": "search optimization", "data_asset": "hotel and flight search logs", "stakeholder": "product analytics", "control": "event completeness", "outcome": "search conversion insight"},
            {"focus": "pricing trends", "data_asset": "cancellation analytics marts", "stakeholder": "revenue analytics", "control": "pricing anomaly", "outcome": "pricing trend visibility"},
        ]
    return [
        {"focus": "enterprise analytics", "data_asset": "operational data feeds", "stakeholder": "analytics", "control": "schema validation", "outcome": "reporting reliability"},
        {"focus": "data governance", "data_asset": "curated data marts", "stakeholder": "business intelligence", "control": "lineage", "outcome": "trusted self-service analytics"},
        {"focus": "operational reporting", "data_asset": "batch and streaming datasets", "stakeholder": "operations", "control": "reconciliation", "outcome": "SLA transparency"},
        {"focus": "data quality", "data_asset": "warehouse models", "stakeholder": "data consumers", "control": "quality", "outcome": "cleaner downstream consumption"},
    ]


def _stable_offset(client_name: str, exp_index: int) -> int:
    return sum(ord(char) for char in client_name.lower()) + (exp_index * 7)


def _apply_alignment_repair(resume: TailoredResume, jd: JobAnalysis, cloud_by_client: Dict[str, str], alignment_pass: int) -> None:
    text = render_resume_text(resume)
    ats = score_resume(resume, text, jd, cloud_by_client.values())
    gaps = ats.get("priority_gaps", {})
    missing_tools = list(gaps.get("technical_tools", []))
    missing_domains = list(gaps.get("domain_terms", []))
    missing_clouds = list(gaps.get("cloud_terms", []))
    missing_responsibilities = list(gaps.get("responsibility_terms", []))

    repair_limit = 6 if alignment_pass == 1 else 12
    tool_terms = missing_tools[:repair_limit]
    domain_terms = missing_domains[:repair_limit]
    responsibility_terms = missing_responsibilities[: max(3, repair_limit // 2)]
    cloud_terms = missing_clouds[:repair_limit]

    _add_repair_terms_to_skills(resume, tool_terms, domain_terms, responsibility_terms)
    _add_repair_terms_to_recent_experiences(resume, tool_terms, domain_terms, responsibility_terms, cloud_terms)
    _add_repair_terms_to_summary(resume, tool_terms, domain_terms)


def _add_repair_terms_to_skills(
    resume: TailoredResume,
    tool_terms: List[str],
    domain_terms: List[str],
    responsibility_terms: List[str],
) -> None:
    if tool_terms:
        resume.technical_skills["Additional ATS Keywords"] = dedupe_keep_order(
            resume.technical_skills.get("Additional ATS Keywords", []) + tool_terms
        )[:40]
    if domain_terms:
        resume.technical_skills["Domain & Business Context"] = dedupe_keep_order(
            resume.technical_skills.get("Domain & Business Context", []) + domain_terms
        )[:24]
    if responsibility_terms:
        resume.technical_skills["Data Engineering Practices"] = dedupe_keep_order(
            resume.technical_skills.get("Data Engineering Practices", []) + responsibility_terms
        )[:24]


def _add_repair_terms_to_recent_experiences(
    resume: TailoredResume,
    tool_terms: List[str],
    domain_terms: List[str],
    responsibility_terms: List[str],
    cloud_terms: List[str],
) -> None:
    recent = resume.experiences[:JD_TAILORED_EXPERIENCE_COUNT]
    if not recent:
        return

    for index, exp in enumerate(recent):
        tools_for_exp = tool_terms[index::JD_TAILORED_EXPERIENCE_COUNT]
        domains_for_exp = domain_terms[index::JD_TAILORED_EXPERIENCE_COUNT]
        responsibilities_for_exp = responsibility_terms[index::JD_TAILORED_EXPERIENCE_COUNT]
        cloud_for_exp = cloud_terms[index::JD_TAILORED_EXPERIENCE_COUNT]
        exp.environment = dedupe_keep_order(exp.environment + tools_for_exp + cloud_for_exp)[:24]

        terms = dedupe_keep_order(domains_for_exp + responsibilities_for_exp + tools_for_exp[:2])
        if terms and exp.responsibilities:
            exp.responsibilities[0] = _append_alignment_phrase(exp.responsibilities[0], terms[:5])


def _add_repair_terms_to_summary(resume: TailoredResume, tool_terms: List[str], domain_terms: List[str]) -> None:
    terms = dedupe_keep_order(tool_terms[:6] + domain_terms[:6])
    if not terms:
        return
    phrase = f" Targeted alignment includes {', '.join(terms)}."
    if resume.summary:
        resume.summary[1 if len(resume.summary) > 1 else 0] = resume.summary[1 if len(resume.summary) > 1 else 0].rstrip(".") + phrase


def _append_alignment_phrase(sentence: str, terms: List[str]) -> str:
    if not terms:
        return sentence
    base = sentence.rstrip(".")
    phrase = f", with added emphasis on {', '.join(terms)}"
    return clamp_words(base + phrase)
