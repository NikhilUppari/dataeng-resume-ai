from __future__ import annotations

from typing import Dict, List

from generators.technical_skills import generate_technical_skills
from parsers.jd_analyzer import JobAnalysis, all_jd_terms
from services.ats_scorer import score_resume
from services.cloud_catalog import expand_cloud_services
from services.domain_detector import infer_job_domain, is_enterprise_domain, keywords_for_domain, same_domain
from services.tailoring_strategy import (
    ADJACENT_PLATFORM_ALIGNMENT,
    DIRECT_DOMAIN_ALIGNMENT,
    LOW_ALIGNMENT,
    TELECOM_DOMAIN,
    TailoringStrategy,
    determine_tailoring_strategy,
    filter_blocked_claim_terms,
)
from services.timeline_validator import filter_timeline_safe, strip_timeline_unsafe_text
from utils.date_format import normalize_display_dates as _normalize_display_dates
from utils.schema import Experience, ResumeProfile, TailoredResume
from utils.technology_terms import extract_known_technologies, is_known_technology
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
RESPONSIBILITY_COUNT_BY_CLIENT_ORDER = [27, 25, 23, 20, 10]
SUMMARY_POINT_COUNT = 12
BULLET_MIN_WORDS = 29
BULLET_MAX_WORDS = 32
BULLET_MIN_TECH_TERMS = 3
BULLET_MAX_TECH_TERMS = 4
BULLET_LENGTHENING_PHRASES = [
    "with throughput tuning, retry behavior, and recovery notes built into daily support",
    "backed by deployment checks, service metrics, and practical support handoff",
    "so lineage, alert context, and production triage stayed easier to follow",
    "using rollout validation, release notes, and incident playbooks for smoother adoption",
    "with partition strategy, alert routing, and capacity reviews kept current",
    "reducing manual review through automation, dashboards, and operating runbooks",
    "with schema controls, reconciliation checks, and peer review supporting cleaner releases",
    "so analytics users received fresher datasets without adding brittle operational steps",
]
TOOL_MENTION_PHRASES = [
    "with {tools} supporting validation",
    "using {tools} for delivery controls",
    "backed by {tools} during release checks",
    "with {tools} improving operational review",
]
RECENT_AI_TOOLS_BY_CLOUD = {
    "AWS": ["SageMaker", "Bedrock", "MLflow"],
    "Azure": ["Azure ML", "Azure OpenAI", "MLflow"],
    "GCP": ["Vertex AI", "Gemini", "MLflow"],
}


def tailor_resume(profile: ResumeProfile, jd: JobAnalysis, cloud_by_client: Dict[str, str], alignment_pass: int = 0) -> TailoredResume:
    job_domain = infer_job_domain(jd)
    strategy = determine_tailoring_strategy(profile, jd, job_domain)
    tailored_experiences = _tailor_experiences(profile.experiences, jd, cloud_by_client, job_domain, strategy)
    skills = generate_technical_skills(profile, jd, cloud_by_client, tailored_experiences, strategy)
    summary = _generate_summary(jd, skills, tailored_experiences, job_domain, strategy)
    placeholder = TailoredResume(
        summary=summary,
        technical_skills=skills,
        experiences=tailored_experiences,
        certifications=profile.certifications,
        education=profile.education,
        ats_score={},
        personal_details=profile.personal_details,
    )
    if alignment_pass > 0:
        _apply_alignment_repair(placeholder, jd, cloud_by_client, alignment_pass, strategy)
    text = render_resume_text(placeholder)
    placeholder.ats_score = score_resume(placeholder, text, jd, cloud_by_client.values(), strategy)
    return placeholder


def render_resume_text(resume: TailoredResume) -> str:
    lines: List[str] = []
    if resume.personal_details:
        lines.extend(resume.personal_details)
        lines.append("")
    lines.append("Professional Summary")
    lines.extend(f"- {item}" for item in resume.summary)
    lines.append("\nTechnical Skills")
    for heading, values in resume.technical_skills.items():
        if values:
            lines.append(f"{heading}: {', '.join(values)}")
    lines.append("\nProfessional Experience")
    for exp in resume.experiences:
        client_header = " | ".join(
            part for part in [exp.client_name, exp.title, _normalize_display_dates(exp.dates)] if part
        )
        lines.append(f"\n{client_header}")
        for bullet in exp.responsibilities:
            lines.append(f"- {bullet}")
        if exp.environment:
            lines.append(f"Environment: {', '.join(exp.environment)}")
    if resume.certifications:
        lines.append("\nCertifications")
        lines.extend(f"- {cert}" for cert in resume.certifications)
    if resume.education:
        lines.append("\nEducation")
        lines.append(resume.education.strip())
    return "\n".join(lines).strip()


def _generate_summary(
    jd: JobAnalysis,
    skills: Dict[str, List[str]],
    experiences: List[Experience],
    job_domain: str,
    strategy: TailoringStrategy,
) -> List[str]:
    clouds = ", ".join(skills.get("Cloud Platforms", [])[:8])
    cloud_focus_terms = dedupe_keep_order(jd.cloud_platforms + skills.get("Cloud Platforms", [])[:4])[:4]
    core_tool_terms = [tool for tool in _summary_tools(jd)[:6] if tool.lower() not in {cloud.lower() for cloud in cloud_focus_terms}]
    core_tools = ", ".join(core_tool_terms[:5])
    cloud_focus = ", ".join(cloud_focus_terms)
    platform_stack = ", ".join(part for part in [cloud_focus or clouds, core_tools or "Python, SQL, Spark"] if part)
    responsibility_focus = _summary_responsibility_focus(jd)
    seniority = jd.seniority_level or "Senior"
    genai = ", ".join(skills.get("AI/ML & GenAI", [])[:4])
    if strategy.name == ADJACENT_PLATFORM_ALIGNMENT and same_domain(strategy.job_domain, TELECOM_DOMAIN):
        adjacent_tools = filter_blocked_claim_terms(dedupe_keep_order(strategy.adjacent_terms + _summary_tools(jd)), strategy)
        adjacent = ", ".join(adjacent_tools[:5])
        return _fit_summary_points([
            f"{seniority} Data Engineer focused on distributed streaming and platform engineering for high-volume event processing with {adjacent}.",
            "Builds reliable ingestion and processing services with practical ownership of throughput tuning, deployment checks, observability, and production recovery.",
            "Applies Kafka and Flink-style design patterns to event-driven workloads while keeping delivery grounded in supported project experience.",
            "Partners with platform and operations teams on containerized releases, alert triage, incident response, and measurable pipeline stability.",
        ], jd, skills, experiences, strategy)
    if strategy.name == ADJACENT_PLATFORM_ALIGNMENT:
        adjacent = ", ".join(strategy.adjacent_terms[:5]) or core_tools
        return _fit_summary_points([
            f"{seniority} Data Engineer building reliable data platforms with {adjacent}, production orchestration, data quality controls, and scalable cloud delivery.",
            "Turns complex job requirements into maintainable pipelines, trusted datasets, deployment runbooks, and reporting layers that operations teams can use confidently.",
            f"Experienced in {responsibility_focus}, translating stakeholder needs into tested ingestion, transformation, monitoring, and release practices.",
            "Brings practical platform habits across capacity planning, partition strategy, incident response, and root-cause analysis for business-critical data workflows.",
        ], jd, skills, experiences, strategy)
    if strategy.name == LOW_ALIGNMENT:
        return _fit_summary_points([
            f"{seniority} Data Engineer focused on reliable data platforms, orchestration, data quality, SQL optimization, and production support.",
            f"Works with {core_tools or 'Python, SQL, Spark'} to build maintainable pipelines, governed datasets, monitoring routines, and operational reporting workflows.",
            f"Experienced in {responsibility_focus}, using structured delivery practices to reduce defects and support timely analytics consumption.",
            "Comfortable moving between legacy ingestion, cloud data services, file distribution, and stakeholder reporting with clear ownership of production outcomes.",
        ], jd, skills, experiences, strategy)
    return _fit_summary_points([
        f"{seniority} Data Engineer building cloud data platforms with {platform_stack} and production-focused delivery practices for analytics and operations teams.",
        "Hands-on engineering spans orchestration, data warehousing, streaming ingestion, governance, SQL tuning, and reusable data quality controls.",
        f"Experienced with {responsibility_focus}, translating business needs into maintainable pipelines, trusted datasets, and measurable reporting outcomes.",
        f"Practical exposure to AI/ML data enablement using {genai} where relevant, while keeping solutions production-focused, compliant, observable, and easy for analytics teams to consume.",
    ], jd, skills, experiences, strategy)


def _fit_summary_points(
    base_points: List[str],
    jd: JobAnalysis,
    skills: Dict[str, List[str]],
    experiences: List[Experience],
    strategy: TailoringStrategy,
) -> List[str]:
    points = dedupe_keep_order(point for point in base_points if point)
    clouds = ", ".join(skills.get("Cloud Platforms", [])[:4]) or "cloud data platforms"
    summary_tools = filter_blocked_claim_terms(_summary_tools(jd), strategy)
    data_tools = ", ".join(summary_tools[:5]) or "Python, SQL, Spark"
    recent_ai = ", ".join(_recent_ai_tools(experiences[0].selected_cloud if experiences else "AWS", experiences[0].dates if experiences else "")[:2])
    if recent_ai:
        recent_ai_phrase = recent_ai
    else:
        recent_ai_phrase = "MLflow and governed feature datasets"
    support_points = [
        f"Recent delivery emphasizes {clouds}, production orchestration, and clear ownership of batch and streaming data workflows for analytics and operations teams.",
        f"Core engineering strengths include {data_tools}, data modeling, SQL optimization, monitoring, and controlled release practices.",
        "Builds data products with practical observability, alerting, runbooks, and root-cause analysis for steady production support.",
        "Uses AI and ML tooling selectively in recent work, including " + recent_ai_phrase + ", for metadata review, feature readiness, and data quality acceleration.",
        "Modernizes legacy ingestion paths, file movement, SFTP handoffs, object storage layouts, and downstream consumption patterns.",
        "Creates maintainable data engineering services with reusable orchestration, validation checks, version control, and stakeholder-ready datasets.",
        "Applies the right platform services for each engagement, balancing job requirements with production readiness, team adoption, and long-term maintainability.",
        "Writes production-minded solutions with capacity review, partition strategy, retry handling, controlled releases, and incident response in mind.",
        "Works across analytics, platform, and operations partners to translate business needs into stable technical delivery.",
        "Improves pipeline reliability through schema controls, reconciliation checks, idempotent processing, and clear escalation paths.",
        "Supports warehouse, lakehouse, and streaming patterns with performance tuning, security controls, and practical documentation.",
        "Communicates tradeoffs clearly with engineers, analysts, and product partners so releases stay understandable after handoff.",
    ]
    for point in support_points:
        if len(points) >= SUMMARY_POINT_COUNT:
            break
        points.append(point)
    return [_fit_summary_word_range(point, index) for index, point in enumerate(points[:SUMMARY_POINT_COUNT])]


def _summary_tools(jd: JobAnalysis) -> List[str]:
    raw_tools = dedupe_keep_order(
        jd.required_skills
        + jd.data_tools
        + jd.etl_tools
        + jd.databases
        + jd.streaming_tools
        + jd.orchestration_tools
        + ["Python", "SQL", "Spark"]
    )
    canonical_tools = extract_known_technologies(" ".join(raw_tools))
    return dedupe_keep_order(canonical_tools + raw_tools)[:10]


def _summary_responsibility_focus(jd: JobAnalysis) -> str:
    terms = dedupe_keep_order(jd.responsibilities + jd.preferred_skills + jd.ats_keywords)
    for term in terms:
        words = term.split()
        if 3 <= len(words) <= 14:
            return _normalize_responsibility_phrase(term.rstrip("."))
    fallback = dedupe_keep_order(jd.data_tools + jd.etl_tools + jd.databases + jd.streaming_tools)
    if fallback:
        return "building " + ", ".join(fallback[:5]) + " solutions"
    return "building batch and streaming data products"


def _normalize_responsibility_phrase(value: str) -> str:
    phrase = value.strip()
    replacements = {
        "build ": "building ",
        "develop ": "developing ",
        "design ": "designing ",
        "create ": "creating ",
        "implement ": "implementing ",
    }
    lower = phrase.lower()
    for prefix, replacement in replacements.items():
        if lower.startswith(prefix):
            return replacement + phrase[len(prefix) :]
    return phrase[:1].lower() + phrase[1:]


SUMMARY_LENGTHENING_PHRASES = [
    "with monitoring, validation, documentation, recovery notes, and support context built into delivery routines",
    "while keeping release notes, recovery steps, performance tuning, and ownership clear",
    "for stable production operations, cleaner stakeholder reporting, and practical support ownership",
    "with practical controls for deployment, review, incident response, and recovery",
    "while keeping performance tuning, data validation, and documentation easy to maintain",
    "with durable handoffs across engineering, analytics, platform, and operations teams",
    "with clear release support context",
    "with practical production context",
    "through support review",
]


def _fit_summary_word_range(text: str, phrase_offset: int = 0) -> str:
    sentence = text.strip().rstrip(".")
    phrase_index = phrase_offset
    while len(sentence.split()) < BULLET_MIN_WORDS:
        current_count = len(sentence.split())
        needed = BULLET_MIN_WORDS - current_count
        remaining = BULLET_MAX_WORDS - current_count
        phrase = _select_summary_extension(needed, remaining, phrase_index)
        sentence = f"{sentence}, {phrase}"
        phrase_index += 1

    tokens = sentence.split()
    if len(tokens) > BULLET_MAX_WORDS:
        tokens = tokens[:BULLET_MAX_WORDS]
    return " ".join(tokens).rstrip(",;") + "."


def _select_summary_extension(needed: int, remaining: int, phrase_offset: int) -> str:
    rotated = SUMMARY_LENGTHENING_PHRASES[phrase_offset % len(SUMMARY_LENGTHENING_PHRASES) :] + SUMMARY_LENGTHENING_PHRASES[: phrase_offset % len(SUMMARY_LENGTHENING_PHRASES)]
    for phrase in rotated:
        count = len(phrase.split())
        if needed <= count <= remaining:
            return phrase
    for phrase in rotated:
        if len(phrase.split()) <= remaining:
            return phrase
    return "through support review"


def _tailor_experiences(
    experiences: List[Experience],
    jd: JobAnalysis,
    cloud_by_client: Dict[str, str],
    job_domain: str,
    strategy: TailoringStrategy,
) -> List[Experience]:
    tailored: List[Experience] = []
    jd_terms = all_jd_terms(jd)
    for index, exp in enumerate(experiences):
        tailor_to_jd = index < JD_TAILORED_EXPERIENCE_COUNT
        selected_cloud = cloud_by_client.get(exp.client_name, exp.selected_cloud or "AWS")
        cloud_context_terms = jd_terms if tailor_to_jd else []
        cloud_tools = filter_timeline_safe(expand_cloud_services(selected_cloud, cloud_context_terms, jd.seniority_level), exp.dates)
        recent_ai_tools = _recent_ai_tools(selected_cloud, exp.dates) if index == 0 else []
        active_domain = _resolve_experience_domain(exp.domain, job_domain, strategy)
        domain_terms = _terms_for_experience_domain(active_domain, jd, job_domain, tailor_to_jd, strategy)
        bullet_count = _responsibility_count_for_client(index)
        responsibilities = _generate_bullets(
            exp,
            jd,
            selected_cloud,
            cloud_tools,
            active_domain,
            domain_terms,
            bullet_count,
            index,
            tailor_to_jd,
            strategy,
            recent_ai_tools,
        )
        environment = _generate_environment(exp, jd, selected_cloud, cloud_tools, index, tailor_to_jd, strategy, recent_ai_tools)
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
    strategy: TailoringStrategy,
    recent_ai_tools: List[str],
) -> List[str]:
    data_tools = _tools_for_experience(exp, jd, tailor_to_jd, exp_index, strategy)
    verbs = ACTION_VERBS[exp_index % len(ACTION_VERBS) :] + ACTION_VERBS[: exp_index % len(ACTION_VERBS)]
    patterns = _patterns_for_strategy(active_domain, strategy)
    focus = _focus_for_strategy(active_domain, exp.client_name, exp_index, strategy)
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
        text = _ensure_tool_mentions(text, [cloud, tool1, tool2, tool3, tool4], idx)
        text = _fit_responsibility_word_range(strip_timeline_unsafe_text(text, exp.dates), idx)
        bullets.append(text)
    if exp_index == 0 and recent_ai_tools:
        bullets = _blend_recent_ai_bullets(bullets, exp, cloud, tools, focus, recent_ai_tools)
    return bullets


def _responsibility_count_for_client(index: int) -> int:
    if index < len(RESPONSIBILITY_COUNT_BY_CLIENT_ORDER):
        return RESPONSIBILITY_COUNT_BY_CLIENT_ORDER[index]
    return RESPONSIBILITY_COUNT_BY_CLIENT_ORDER[-1]


def _recent_ai_tools(cloud: str, dates: str) -> List[str]:
    tools = RECENT_AI_TOOLS_BY_CLOUD.get(cloud, RECENT_AI_TOOLS_BY_CLOUD["AWS"])
    return filter_timeline_safe(tools, dates)[:3]


def _blend_recent_ai_bullets(
    bullets: List[str],
    exp: Experience,
    cloud: str,
    tools: List[str],
    focus: List[Dict[str, str]],
    recent_ai_tools: List[str],
) -> List[str]:
    if not bullets:
        return bullets
    replacements = []
    ai_tool = recent_ai_tools[0]
    second_ai_tool = recent_ai_tools[1] if len(recent_ai_tools) > 1 else recent_ai_tools[0]
    tool1 = tools[0] if tools else "Python"
    tool2 = tools[3 % len(tools)] if tools else "SQL"
    data_asset = focus[0]["data_asset"] if focus else "curated data feeds"
    stakeholder = focus[0]["stakeholder"] if focus else "analytics"
    replacements.append(
        (
            min(4, len(bullets) - 1),
            (
                f"Added lightweight {ai_tool} checks around {data_asset} metadata using {tool1}, {tool2}, and SQL, "
                f"helping {stakeholder} users spot quality issues without turning the pipeline into an AI project."
            ),
        )
    )
    if len(bullets) > 12:
        replacements.append(
            (
                min(13, len(bullets) - 1),
                (
                    f"Paired {second_ai_tool} experiments with governed feature datasets on {cloud}, keeping approvals, "
                    f"lineage, and rollback notes clear while core ingestion stayed focused on reliable data delivery."
                ),
            )
        )
    updated = list(bullets)
    for index, text in replacements:
        text = _ensure_tool_mentions(text, [cloud, ai_tool, second_ai_tool, tool1, tool2, "SQL"], index)
        updated[index] = _fit_responsibility_word_range(strip_timeline_unsafe_text(text, exp.dates), index)
    return updated


def _generate_environment(
    exp: Experience,
    jd: JobAnalysis,
    cloud: str,
    cloud_tools: List[str],
    exp_index: int,
    tailor_to_jd: bool,
    strategy: TailoringStrategy,
    recent_ai_tools: List[str] | None = None,
) -> List[str]:
    transfer_tools = _transferable_platform_tools(jd, strategy)
    if tailor_to_jd:
        base = dedupe_keep_order(
            [cloud]
            + transfer_tools
            + jd.data_tools
            + jd.databases
            + jd.orchestration_tools
            + jd.streaming_tools
            + list(recent_ai_tools or [])
            + ["Python", "SQL", "Git", "CI/CD", "data quality"]
            + cloud_tools
        )
    else:
        jd_subset = _jd_tool_subset_for_older_experience(jd, exp.client_name, exp_index)
        base = dedupe_keep_order([cloud] + transfer_tools[:8] + jd_subset + cloud_tools + exp.environment + BASELINE_DATA_STACK)
    complexity = 40
    return filter_timeline_safe(base[:complexity], exp.dates)


def _resolve_experience_domain(exp_domain: str, job_domain: str, strategy: TailoringStrategy) -> str:
    if strategy.name in {ADJACENT_PLATFORM_ALIGNMENT, LOW_ALIGNMENT}:
        return exp_domain or "Enterprise Data Engineering"
    if is_enterprise_domain(exp_domain) and not is_enterprise_domain(job_domain):
        return job_domain
    return exp_domain or job_domain


def _terms_for_experience_domain(
    exp_domain: str,
    jd: JobAnalysis,
    job_domain: str,
    tailor_to_jd: bool,
    strategy: TailoringStrategy,
) -> List[str]:
    terms = _resume_safe_domain_terms(exp_domain)
    if strategy.name == ADJACENT_PLATFORM_ALIGNMENT:
        return dedupe_keep_order(terms)
    if tailor_to_jd and same_domain(exp_domain, job_domain):
        terms = _resume_safe_jd_domain_terms(jd.domain_keywords, exp_domain) + terms
    return dedupe_keep_order(terms)


def _resume_safe_domain_terms(domain: str) -> List[str]:
    if same_domain(domain, "Financial Services / Banking / Wealth Management / Asset Servicing"):
        return ["financial services", "risk reporting", "transaction data", "audit reporting", "reconciliation"]
    if same_domain(domain, "Healthcare"):
        return ["healthcare data", "claims data", "clinical reporting", "provider analytics", "pharmacy data"]
    if same_domain(domain, "Retail / E-commerce"):
        return ["retail data", "order pipelines", "inventory analytics", "seller analytics", "customer analytics"]
    if same_domain(domain, "Aviation"):
        return ["aviation data", "flight operations", "crew scheduling", "maintenance analytics", "passenger analytics"]
    if same_domain(domain, "Travel / Online Travel Platform"):
        return ["travel data", "booking analytics", "itinerary data", "pricing trends", "customer segmentation"]
    return keywords_for_domain(domain)


def _resume_safe_jd_domain_terms(terms: List[str], exp_domain: str) -> List[str]:
    blocked = []
    if same_domain(exp_domain, "Financial Services / Banking / Wealth Management / Asset Servicing"):
        blocked = ["banking", "wealth management", "asset servicing"]
    return [term for term in terms if term and term.lower() not in blocked]


def _tools_for_experience(exp: Experience, jd: JobAnalysis, tailor_to_jd: bool, exp_index: int, strategy: TailoringStrategy) -> List[str]:
    transfer_tools = _transferable_platform_tools(jd, strategy)
    if tailor_to_jd:
        return dedupe_keep_order(
            transfer_tools
            + jd.data_tools
            + jd.etl_tools
            + jd.databases
            + jd.streaming_tools
            + jd.orchestration_tools
            + ["Python", "SQL", "Spark"]
        )
    return dedupe_keep_order(transfer_tools[:8] + _jd_tool_subset_for_older_experience(jd, exp.client_name, exp_index) + exp.environment + BASELINE_DATA_STACK)


def _transferable_platform_tools(jd: JobAnalysis, strategy: TailoringStrategy) -> List[str]:
    if strategy.name != ADJACENT_PLATFORM_ALIGNMENT:
        return []
    return filter_blocked_claim_terms(
        dedupe_keep_order(
            strategy.adjacent_terms
            + jd.streaming_tools
            + jd.orchestration_tools
            + jd.databases
            + jd.required_skills
            + jd.preferred_skills
            + ["Kafka", "Flink", "Kubernetes", "OpenShift", "Helm", "Java", "Spring Boot", "Prometheus", "Grafana", "OpenTelemetry", "Jaeger"]
        ),
        strategy,
    )


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


def _ensure_tool_mentions(text: str, tools: List[str], phrase_offset: int = 0) -> str:
    unique_tools = dedupe_keep_order(tool for tool in tools if tool and is_known_technology(tool))
    if not unique_tools:
        return text
    present = extract_known_technologies(text, unique_tools)
    missing = [tool for tool in unique_tools if tool.lower() not in {item.lower() for item in present}]
    needed = max(0, BULLET_MIN_TECH_TERMS - len(present))
    if needed == 0 or not missing:
        return text
    additions = missing[: min(needed, max(0, BULLET_MAX_TECH_TERMS - len(present)))]
    if not additions:
        return text
    phrase = TOOL_MENTION_PHRASES[phrase_offset % len(TOOL_MENTION_PHRASES)]
    return text.rstrip(".") + ", " + phrase.format(tools=", ".join(additions)) + "."


def _fit_responsibility_word_range(text: str, phrase_offset: int = 0) -> str:
    sentence = text.strip().rstrip(".")
    phrase_index = phrase_offset
    while len(sentence.split()) < BULLET_MIN_WORDS:
        phrase = BULLET_LENGTHENING_PHRASES[phrase_index % len(BULLET_LENGTHENING_PHRASES)]
        sentence = f"{sentence}, {phrase}"
        phrase_index += 1

    tokens = sentence.split()
    if len(tokens) > BULLET_MAX_WORDS:
        tokens = tokens[:BULLET_MAX_WORDS]
    return " ".join(tokens).rstrip(",;") + "."


def _patterns_for_strategy(domain: str, strategy: TailoringStrategy) -> List[str]:
    if strategy.name == ADJACENT_PLATFORM_ALIGNMENT and same_domain(strategy.job_domain, TELECOM_DOMAIN):
        return [
            "{verb} high-volume event ingestion for {data_asset} on {cloud} using {tool1}, {tool2}, and {tool3}, improving throughput and recovery for {stakeholder} teams.",
            "{verb} distributed streaming workflows with {tool1}, {tool2}, and {tool3}, tuning partition strategy, retry handling, and back-pressure controls for operational workloads.",
            "{verb} platform services around {data_asset} using {tool1} and {tool2}, improving async processing, file movement, and downstream handoff for {stakeholder} users.",
            "{verb} observability and incident workflows across {tool1}, {tool2}, and {tool3}, strengthening SLO tracking, alert triage, and root-cause analysis.",
            "{verb} containerized deployment patterns using {tool1}, {tool2}, and {tool3}, supporting repeatable releases, capacity reviews, and production support handoffs.",
            "{verb} file ingestion and distribution paths with {tool1}, {tool2}, and SQL, improving partition pruning, validation checks, and controlled data delivery.",
            "{verb} batch and streaming reliability patterns with {tool1}, {tool2}, and {tool3}, helping teams operate fresher event data with safer rollback options.",
        ]
    return _patterns_for_domain(domain)


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


def _focus_for_strategy(domain: str, client_name: str, exp_index: int, strategy: TailoringStrategy) -> List[Dict[str, str]]:
    if strategy.name == ADJACENT_PLATFORM_ALIGNMENT and same_domain(strategy.job_domain, TELECOM_DOMAIN):
        focus = [
            {"focus": "streaming ingestion", "data_asset": "operational event streams", "stakeholder": "platform operations", "control": "schema validation", "outcome": "processing reliability"},
            {"focus": "platform reliability", "data_asset": "distributed processing jobs", "stakeholder": "SRE and application", "control": "SLO monitoring", "outcome": "incident response speed"},
            {"focus": "file distribution", "data_asset": "SFTP and object-storage feeds", "stakeholder": "downstream integration", "control": "reconciliation", "outcome": "delivery traceability"},
            {"focus": "service orchestration", "data_asset": "containerized pipeline services", "stakeholder": "release management", "control": "deployment validation", "outcome": "release stability"},
        ]
        offset = exp_index % len(focus)
        return focus[offset:] + focus[:offset]
    return _focus_for_experience(domain, client_name, exp_index)


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
            {"focus": "client reporting", "data_asset": "financial services datasets", "stakeholder": "operations", "control": "KYC validation", "outcome": "reporting accuracy"},
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


def _apply_alignment_repair(
    resume: TailoredResume,
    jd: JobAnalysis,
    cloud_by_client: Dict[str, str],
    alignment_pass: int,
    strategy: TailoringStrategy,
) -> None:
    text = render_resume_text(resume)
    ats = score_resume(resume, text, jd, cloud_by_client.values(), strategy)
    gaps = ats.get("priority_gaps", {})
    missing_tools = list(gaps.get("technical_tools", []))
    missing_domains = list(gaps.get("domain_terms", []))
    missing_clouds = list(gaps.get("cloud_terms", []))
    missing_responsibilities = list(gaps.get("responsibility_terms", []))

    repair_limit = 6 if alignment_pass == 1 else 12
    tool_terms = missing_tools[:repair_limit]
    source_text = render_resume_text(resume)
    if strategy.name == DIRECT_DOMAIN_ALIGNMENT:
        domain_terms = filter_blocked_claim_terms(missing_domains[:repair_limit], strategy, source_text)
        responsibility_terms = filter_blocked_claim_terms(missing_responsibilities[: max(3, repair_limit // 2)], strategy, source_text)
    else:
        domain_terms = []
        responsibility_terms = []
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
        _add_tools_to_existing_skill_categories(resume, tool_terms)


def _add_tools_to_existing_skill_categories(resume: TailoredResume, tool_terms: List[str]) -> None:
    category_rules = [
        ("Cloud Platforms", ["AWS", "Azure", "GCP", "Redshift", "BigQuery", "Synapse"]),
        ("Big Data Technologies", ["Spark", "PySpark", "Databricks", "Delta Lake", "Hadoop", "Hive", "dbt"]),
        ("Data Engineering & ETL", ["Glue", "Airflow", "ADF", "Dataflow", "Informatica", "Talend", "SSIS"]),
        ("Databases", ["Snowflake", "Oracle", "SQL Server", "PostgreSQL", "MySQL", "DynamoDB", "MongoDB"]),
        ("Streaming & Messaging", ["Kafka", "Kinesis", "Flink", "Pub/Sub", "Event Hub", "MSK"]),
        ("Programming Languages", ["Python", "SQL", "Java", "Golang", "Go", "Scala", "PL/SQL"]),
        ("DevOps & CI/CD", ["Docker", "Kubernetes", "OpenShift", "Helm", "Terraform", "Jenkins", "CI/CD"]),
        ("Monitoring & Observability", ["CloudWatch", "Prometheus", "Grafana", "OpenTelemetry", "Jaeger", "ELK", "EFK"]),
    ]
    for term in tool_terms:
        placed = False
        for category, markers in category_rules:
            if any(marker.lower() in term.lower() for marker in markers):
                resume.technical_skills[category] = dedupe_keep_order(resume.technical_skills.get(category, []) + [term])[:16]
                placed = True
                break
        if not placed:
            resume.technical_skills["Data Engineering & ETL"] = dedupe_keep_order(
                resume.technical_skills.get("Data Engineering & ETL", []) + [term]
            )[:16]


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
    terms = dedupe_keep_order(tool_terms[:4] + domain_terms[:2])
    if not terms:
        return
    if resume.summary:
        index = 1 if len(resume.summary) > 1 else 0
        resume.summary[index] = _fit_summary_word_range(
            resume.summary[index].rstrip(".") + f", using {', '.join(terms)} where they support pipeline design and production delivery",
            index,
        )


def _append_alignment_phrase(sentence: str, terms: List[str]) -> str:
    if not terms:
        return sentence
    base = sentence.rstrip(".")
    phrase = f", with added emphasis on {', '.join(terms)}"
    return clamp_words(base + phrase)
