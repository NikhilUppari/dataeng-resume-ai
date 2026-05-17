from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List

import streamlit as st

from generators.resume_tailor import render_resume_text, tailor_resume
from parsers.jd_analyzer import analyze_jd
from parsers.resume_parser import extract_resume_text, parse_resume_text
from services.domain_detector import detect_domain
from services.ollama_client import OllamaClient, OllamaError
from services.resume_quality_gate import evaluate_resume_quality
from utils.docx_exporter import build_docx
from utils.pdf_exporter import build_pdf
from utils.schema import JobAnalysis, ResumeProfile


APP_DIR = Path(__file__).resolve().parent
MODELS = ["llama3.1", "qwen2.5", "mistral", "deepseek-r1"]
CLOUDS = ["AWS", "Azure", "GCP"]
PARSER_CACHE_VERSION = "known-client-v3"
MAX_ALIGNMENT_ATTEMPTS = 3


def main() -> None:
    st.set_page_config(page_title="dataeng-resume-ai", page_icon="D", layout="wide")
    _inject_css()

    st.title("dataeng-resume-ai")

    with st.sidebar:
        st.header("Local AI")
        model = st.selectbox("Ollama model", MODELS, index=0)
        ollama = OllamaClient()
        available = ollama.is_available()
        model_ready = available and ollama.has_model(model)
        if model_ready:
            st.status("Ollama connected", state="complete")
        elif available:
            st.status(f"Model not found: {model}", state="warning")
            st.caption(f"Run `ollama pull {model}` in PowerShell, then refresh.")
        else:
            st.status("Ollama not detected", state="error")
        use_ai = st.toggle("Use Ollama enrichment", value=model_ready, disabled=not model_ready)
        st.divider()
        if st.button("Load sample JD"):
            st.session_state["jd_text"] = (APP_DIR / "sample_data" / "sample_job_description.txt").read_text(encoding="utf-8")

    left, right = st.columns([0.95, 1.05], gap="large")

    with left:
        uploaded_file = st.file_uploader("Resume upload", type=["docx", "pdf", "txt"])
        jd_text = st.text_area("Job description", key="jd_text", height=360, placeholder="Paste the target job description here...")

        profile = _get_profile(uploaded_file)
        if profile:
            st.subheader("Client cloud selection")
            cloud_by_client = _cloud_controls(profile)
            _experience_table(profile, cloud_by_client)
        else:
            cloud_by_client = {}

        generate = st.button("Generate tailored resume", type="primary", use_container_width=True, disabled=not (profile and jd_text.strip()))
        build_log_placeholder = st.empty()

    if generate and profile:
        _reset_build_log()

        def log_status(message: str) -> None:
            _append_build_log(message)
            _render_build_log(build_log_placeholder, st.session_state["build_log"])

        with st.spinner("Tailoring, scoring, and validating resume alignment..."):
            log_status("Resume builder in action. Reading the JD and pretending this is totally casual.")
            jd = _analyze_jd(jd_text, model, use_ai, ollama, log_status)
            tailored, quality, attempts = _generate_quality_checked_resume(profile, jd, cloud_by_client, log_status)
            st.session_state["tailored_resume"] = tailored
            st.session_state["jd_analysis"] = jd
            st.session_state["resume_quality"] = quality
            st.session_state["alignment_attempts"] = attempts
            st.session_state["resume_text"] = render_resume_text(tailored)
            if quality["passed"]:
                log_status("Building DOCX now. The resume has earned paperwork privileges.")
                st.session_state["docx_bytes"] = build_docx(tailored)
                log_status("Trying PDF export too. This part depends on your local converter behaving itself.")
                st.session_state["pdf_bytes"] = build_pdf(tailored)
                if st.session_state["pdf_bytes"] is None:
                    log_status("PDF converter said no today. DOCX is still ready.")
                else:
                    log_status("PDF is ready too. Very civilized.")
            else:
                st.session_state.pop("docx_bytes", None)
                st.session_state.pop("pdf_bytes", None)
                log_status("Downloads are staying locked because the score still needs work.")

    with right:
        _results_panel()


def _get_profile(uploaded_file) -> ResumeProfile | None:
    if uploaded_file is None:
        return None
    cache_key = f"profile_{PARSER_CACHE_VERSION}_{uploaded_file.name}_{uploaded_file.size}"
    if cache_key not in st.session_state:
        with st.spinner("Parsing resume..."):
            text = extract_resume_text(uploaded_file)
            profile = parse_resume_text(text)
            for exp in profile.experiences:
                exp.domain = detect_domain(exp.client_name, exp.raw_text)
            st.session_state[cache_key] = profile
    return st.session_state[cache_key]


def _cloud_controls(profile: ResumeProfile) -> Dict[str, str]:
    cloud_by_client: Dict[str, str] = {}
    for index, exp in enumerate(profile.experiences):
        default_cloud = _guess_cloud(exp.raw_text)
        key = f"cloud_{index}_{exp.client_name}"
        cloud_by_client[exp.client_name] = st.selectbox(exp.client_name, CLOUDS, index=CLOUDS.index(default_cloud), key=key)
    return cloud_by_client


def _experience_table(profile: ResumeProfile, cloud_by_client: Dict[str, str]) -> None:
    rows = ["| Client | Title | Dates | Domain | Cloud |", "| --- | --- | --- | --- | --- |"]
    for exp in profile.experiences:
        rows.append(
            " | ".join(
                [
                    f"| {_markdown_table_cell(exp.client_name)}",
                    _markdown_table_cell(exp.title),
                    _markdown_table_cell(exp.dates),
                    _markdown_table_cell(exp.domain),
                    f"{_markdown_table_cell(cloud_by_client.get(exp.client_name, 'AWS'))} |",
                ]
            )
        )
    st.markdown("\n".join(rows))


def _markdown_table_cell(value: str) -> str:
    return str(value or "-").replace("|", "\\|").replace("\n", " ").strip()


def _analyze_jd(
    jd_text: str,
    model: str,
    use_ai: bool,
    ollama: OllamaClient,
    log_status: Callable[[str], None] | None = None,
) -> JobAnalysis:
    _log(log_status, "Analyzing JD skills, tools, seniority, and domain hints.")
    analysis = analyze_jd(jd_text)
    if not use_ai:
        _log(log_status, "Using local JD analysis. No model drama, just deterministic work.")
        return analysis

    prompt = (APP_DIR / "prompts" / "jd_analysis_prompt.txt").read_text(encoding="utf-8")
    try:
        _log(log_status, f"Asking {model} to enrich the JD analysis. It has up to 8 minutes, no rushing the chef.")
        payload = ollama.generate_json(model, f"{prompt}\n\nJOB DESCRIPTION:\n{jd_text}")
    except OllamaError as exc:
        st.warning(f"{exc}. Using local fallback analysis for this run.")
        _log(log_status, "Ollama did not finish cleanly, so local fallback is taking over.")
        return analysis
    if not payload:
        _log(log_status, "AI returned no usable JSON. Local JD analysis stays in charge.")
        return analysis

    for field in analysis.__dataclass_fields__:
        value = payload.get(field)
        if isinstance(getattr(analysis, field), list) and isinstance(value, list):
            setattr(analysis, field, [str(item) for item in value if str(item).strip()])
        elif field == "seniority_level" and isinstance(value, str):
            analysis.seniority_level = value
    _log(log_status, "JD analysis enriched. The app now has a better target to aim at.")
    return analysis


def _generate_quality_checked_resume(
    profile: ResumeProfile,
    jd: JobAnalysis,
    cloud_by_client: Dict[str, str],
    log_status: Callable[[str], None] | None = None,
):
    latest_quality = {}
    latest_tailored = None
    _log(log_status, "Lining up clients, domains, selected clouds, and the recent-three tailoring rule.")
    for index, exp in enumerate(profile.experiences, start=1):
        mode = "full JD tailoring" if index <= 3 else "half JD tools plus domain-safe cloud depth"
        cloud = cloud_by_client.get(exp.client_name, exp.selected_cloud or "AWS")
        _log(log_status, f"Working on client {index}: {exp.client_name} | {exp.domain} | {cloud} | {mode}.")

    for attempt_index in range(MAX_ALIGNMENT_ATTEMPTS):
        if attempt_index == 0:
            _log(log_status, "Attempt 1: building the first tailored draft. Optimism is high.")
        elif attempt_index == 1:
            _log(log_status, "Urghhhhh, score is low. Let me work again and tighten the match.")
        else:
            _log(log_status, "Starting again. Such a boring task, but the resume deserves better.")
        tailored = tailor_resume(profile, jd, cloud_by_client, alignment_pass=attempt_index)
        quality = evaluate_resume_quality(tailored.ats_score)
        latest_tailored = tailored
        latest_quality = quality
        ats = tailored.ats_score
        _log(
            log_status,
            (
                f"Checking ATS: overall {ats['ats_match_percentage']}%, technical {ats['keyword_score']}%, "
                f"cloud {ats['cloud_alignment_score']}%, domain {ats['domain_alignment_score']}%."
            ),
        )
        if quality["passed"]:
            _log(log_status, f"Finallllyyyyyy resume is ready after {attempt_index + 1} attempt(s). Downloads unlocked.")
            return tailored, quality, attempt_index + 1
        for failure in quality.get("failures", []):
            _log(log_status, f"Gate says nope: {failure}")
        _log(log_status, "Repair pass coming up. Time to patch the gaps without keyword stuffing.")
    _log(log_status, "I tried every alignment pass. This one still needs human review before downloads.")
    return latest_tailored, latest_quality, MAX_ALIGNMENT_ATTEMPTS


def _results_panel() -> None:
    tailored = st.session_state.get("tailored_resume")
    if not tailored:
        st.subheader("Resume preview")
        st.info("Upload a resume, paste a JD, select clouds, and generate.")
        return

    ats = tailored.ats_score
    quality = st.session_state.get("resume_quality") or evaluate_resume_quality(ats)
    attempts = st.session_state.get("alignment_attempts", 1)
    score_cols = st.columns(3)
    score_cols[0].metric("ATS match", f"{ats['ats_match_percentage']}%")
    score_cols[0].caption(ats.get("score_breakdown", {}).get("overall", ""))
    score_cols[1].metric("Cloud alignment", f"{ats['cloud_alignment_score']}%")
    score_cols[1].caption(ats.get("score_breakdown", {}).get("cloud", ""))
    score_cols[2].metric("Domain alignment", f"{ats['domain_alignment_score']}%")
    score_cols[2].caption(ats.get("score_breakdown", {}).get("domain", ""))
    if ats.get("domain_gap_warning"):
        st.warning(ats["domain_gap_warning"])

    if quality["passed"]:
        if quality.get("adjacent_platform_fit"):
            st.success(f"Resume passed the adjacent platform fit gate after {attempts} attempt(s). Downloads are enabled with the domain-gap warning above.")
        else:
            st.success(f"Resume passed the JD alignment gate after {attempts} attempt(s). Downloads are enabled.")
    else:
        st.error(f"Resume did not pass the JD alignment gate after {attempts} attempt(s). Downloads are disabled until gaps are fixed.")
        for failure in quality.get("failures", []):
            st.write(f"- {failure}")

    _show_build_log()

    st.subheader("Downloads")
    download_cols = st.columns(2)
    download_cols[0].download_button(
        "Download DOCX",
        data=st.session_state.get("docx_bytes", b""),
        file_name="tailored_data_engineer_resume.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        disabled=not quality["passed"],
        use_container_width=True,
    )
    pdf_bytes = st.session_state.get("pdf_bytes")
    download_cols[1].download_button(
        "Download PDF",
        data=pdf_bytes or b"",
        file_name="tailored_data_engineer_resume.pdf",
        mime="application/pdf",
        disabled=(not quality["passed"]) or pdf_bytes is None,
        use_container_width=True,
    )
    if quality["passed"] and pdf_bytes is None:
        st.caption("PDF export needs Microsoft Word/docx2pdf or a working Pandoc PDF toolchain.")

    st.subheader("Resume preview")
    st.text_area("Generated resume", st.session_state["resume_text"], height=520)

    with st.expander("ATS keyword analysis", expanded=True):
        st.write(f"Technical match: {ats['keyword_score']}% ({ats.get('score_breakdown', {}).get('technical', 'Not rated')})")
        col_a, col_b = st.columns(2)
        col_a.write("Matched keywords")
        col_a.write(", ".join(ats["matched_keywords"][:80]) or "None")
        col_b.write("Missing keywords")
        col_b.write(", ".join(ats["missing_keywords"][:80]) or "None")

        st.write("Priority gaps")
        gaps = ats.get("priority_gaps", {})
        gap_cols = st.columns(4)
        gap_cols[0].write("Technical tools")
        gap_cols[0].write(", ".join(gaps.get("technical_tools", [])[:20]) or "None")
        gap_cols[1].write("Domain terms")
        gap_cols[1].write(", ".join(gaps.get("domain_terms", [])[:20]) or "None")
        gap_cols[2].write("Cloud terms")
        gap_cols[2].write(", ".join(gaps.get("cloud_terms", [])[:20]) or "None")
        gap_cols[3].write("Responsibilities")
        gap_cols[3].write(", ".join(gaps.get("responsibility_terms", [])[:20]) or "None")

        st.write("Suggestions")
        for suggestion in ats["suggestions"]:
            st.write(f"- {suggestion}")

    with st.expander("JD analysis JSON"):
        jd = st.session_state.get("jd_analysis")
        st.code(json.dumps(jd.__dict__ if jd else {}, indent=2), language="json")


def _guess_cloud(text: str) -> str:
    lower = (text or "").lower()
    if any(term in lower for term in ["azure", "adls", "synapse", "data factory"]):
        return "Azure"
    if any(term in lower for term in ["gcp", "bigquery", "pub/sub", "dataflow"]):
        return "GCP"
    return "AWS"


def _reset_build_log() -> None:
    st.session_state["build_log"] = []


def _append_build_log(message: str) -> None:
    st.session_state.setdefault("build_log", []).append(message)


def _render_build_log(target, messages: List[str]) -> None:
    with target.container():
        st.subheader("Build log")
        for message in messages[-12:]:
            st.write(f"- {message}")


def _show_build_log() -> None:
    messages = st.session_state.get("build_log", [])
    if not messages:
        return
    with st.expander("Resume builder log", expanded=True):
        for message in messages:
            st.write(f"- {message}")


def _log(log_status: Callable[[str], None] | None, message: str) -> None:
    if log_status:
        log_status(message)


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; max-width: 1500px; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; }
        textarea { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
