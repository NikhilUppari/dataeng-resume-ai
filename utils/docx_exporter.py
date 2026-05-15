from __future__ import annotations

from io import BytesIO
from typing import Iterable

from docx import Document
from docx.shared import Inches, Pt

from utils.schema import TailoredResume


def build_docx(resume: TailoredResume) -> bytes:
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)

    styles = document.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(10.5)

    _heading(document, "PROFESSIONAL SUMMARY")
    for item in resume.summary:
        _bullet(document, item)

    _heading(document, "TECHNICAL SKILLS")
    for heading, values in resume.technical_skills.items():
        if values:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(2)
            run = paragraph.add_run(f"{heading}: ")
            run.bold = True
            _add_tools_run(paragraph, values)

    _heading(document, "PROFESSIONAL EXPERIENCE")
    for exp in resume.experiences:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        client = paragraph.add_run(f"Client: {exp.client_name}")
        client.bold = True
        if exp.domain:
            paragraph.add_run(f" | {exp.domain}")

        if exp.title or exp.dates:
            title = document.add_paragraph()
            title.paragraph_format.space_after = Pt(2)
            title.add_run(exp.title).bold = True
            if exp.dates:
                title.add_run(f" | {exp.dates}")

        for bullet in exp.responsibilities:
            _bullet_with_bold_tools(document, bullet, exp.environment)

        if exp.environment:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(6)
            paragraph.add_run("Environment: ").bold = True
            _add_tools_run(paragraph, exp.environment)

    if resume.certifications:
        _heading(document, "CERTIFICATIONS")
        for cert in resume.certifications:
            _bullet(document, cert)

    if resume.education:
        _heading(document, "EDUCATION")
        for line in resume.education.splitlines():
            if line.strip():
                document.add_paragraph(line.strip())

    output = BytesIO()
    document.save(output)
    return output.getvalue()


def _heading(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(8)
    paragraph.paragraph_format.space_after = Pt(3)
    run = paragraph.add_run(text)
    run.bold = True
    run.font.size = Pt(11)


def _bullet(document: Document, text: str) -> None:
    paragraph = document.add_paragraph(style="List Bullet")
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.add_run(text)


def _bullet_with_bold_tools(document: Document, text: str, tools: Iterable[str]) -> None:
    paragraph = document.add_paragraph(style="List Bullet")
    paragraph.paragraph_format.space_after = Pt(2)
    matches = []
    lower = text.lower()
    for tool in sorted(set(tools), key=len, reverse=True):
        start = lower.find(tool.lower())
        if start >= 0:
            end = start + len(tool)
            if not any(start < existing_end and end > existing_start for existing_start, existing_end, _ in matches):
                matches.append((start, end, text[start:end]))
    matches.sort(key=lambda item: item[0])

    cursor = 0
    for start, end, matched_text in matches:
        if cursor < start:
            paragraph.add_run(text[cursor:start])
        paragraph.add_run(matched_text).bold = True
        cursor = end
    if cursor < len(text):
        paragraph.add_run(text[cursor:])


def _add_tools_run(paragraph, values: Iterable[str]) -> None:
    values = [value for value in values if value]
    for index, value in enumerate(values):
        if index:
            paragraph.add_run(", ")
        paragraph.add_run(value).bold = True
