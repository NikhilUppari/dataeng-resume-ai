from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import streamlit as st

from generators.resume_tailor import render_resume_text, tailor_resume
from parsers.jd_analyzer import analyze_jd
from parsers.resume_parser import extract_resume_text, parse_resume_text
from services.domain_detector import detect_domain
from services.ollama_client import OllamaClient
from utils.docx_exporter import build_docx
from utils.pdf_exporter import build_pdf
from utils.schema import JobAnalysis, ResumeProfile


APP_DIR = Path(__file__).resolve().parent
MODELS = ["llama3.1", "qwen2.5", "mistral", "deepseek-r1"]
CLOUDS = ["AWS", "Azure", "GCP"]
PARSER_CACHE_VERSION = "known-client-v2"


def main() -> None:
    st.set_page_config(page_title="dataeng-resume-ai", page_icon="D", layout="wide")
    _inject_css()

    st.title("dataeng-resume-ai")

    with st.sidebar:
        st.header("Local AI")
        model = st.selectbox("Ollama model", MODELS, index=0)
        ollama = OllamaClient()
        available = ollama.is_available()
        st.status("Ollama connected" if available else "Ollama not detected", state="complete" if available else "error")
        use_ai = st.toggle("Use Ollama enrichment", value=available, disabled=not available)
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

    if generate and profile:
        with st.spinner("Tailoring resume locally..."):
            jd = _analyze_jd(jd_text, model, use_ai, ollama)
            tailored = tailor_resume(profile, jd, cloud_by_client)
            st.session_state["tailored_resume"] = tailored
            st.session_state["jd_analysis"] = jd
            st.session_state["resume_text"] = render_resume_text(tailored)
            st.session_state["docx_bytes"] = build_docx(tailored)
            st.session_state["pdf_bytes"] = build_pdf(tailored)

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
    rows = [
        {
            "Client": exp.client_name,
            "Title": exp.title,
            "Dates": exp.dates,
            "Domain": exp.domain,
            "Cloud": cloud_by_client.get(exp.client_name, "AWS"),
        }
        for exp in profile.experiences
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _analyze_jd(jd_text: str, model: str, use_ai: bool, ollama: OllamaClient) -> JobAnalysis:
    analysis = analyze_jd(jd_text)
    if not use_ai:
        return analysis

    prompt = (APP_DIR / "prompts" / "jd_analysis_prompt.txt").read_text(encoding="utf-8")
    payload = ollama.generate_json(model, f"{prompt}\n\nJOB DESCRIPTION:\n{jd_text}")
    if not payload:
        return analysis

    for field in analysis.__dataclass_fields__:
        value = payload.get(field)
        if isinstance(getattr(analysis, field), list) and isinstance(value, list):
            setattr(analysis, field, [str(item) for item in value if str(item).strip()])
        elif field == "seniority_level" and isinstance(value, str):
            analysis.seniority_level = value
    return analysis


def _results_panel() -> None:
    tailored = st.session_state.get("tailored_resume")
    if not tailored:
        st.subheader("Resume preview")
        st.info("Upload a resume, paste a JD, select clouds, and generate.")
        return

    ats = tailored.ats_score
    score_cols = st.columns(3)
    score_cols[0].metric("ATS match", f"{ats['ats_match_percentage']}%")
    score_cols[1].metric("Cloud alignment", f"{ats['cloud_alignment_score']}%")
    score_cols[2].metric("Domain alignment", f"{ats['domain_alignment_score']}%")

    st.subheader("Downloads")
    download_cols = st.columns(2)
    download_cols[0].download_button(
        "Download DOCX",
        data=st.session_state["docx_bytes"],
        file_name="tailored_data_engineer_resume.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
    pdf_bytes = st.session_state.get("pdf_bytes")
    download_cols[1].download_button(
        "Download PDF",
        data=pdf_bytes or b"",
        file_name="tailored_data_engineer_resume.pdf",
        mime="application/pdf",
        disabled=pdf_bytes is None,
        use_container_width=True,
    )
    if pdf_bytes is None:
        st.caption("PDF export needs Microsoft Word/docx2pdf or a working Pandoc PDF toolchain.")

    st.subheader("Resume preview")
    st.text_area("Generated resume", st.session_state["resume_text"], height=520)

    with st.expander("ATS keyword analysis", expanded=True):
        col_a, col_b = st.columns(2)
        col_a.write("Matched keywords")
        col_a.write(", ".join(ats["matched_keywords"][:80]) or "None")
        col_b.write("Missing keywords")
        col_b.write(", ".join(ats["missing_keywords"][:80]) or "None")
        st.write("Missing tools")
        st.write(", ".join(ats["missing_tools"][:60]) or "None")
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
