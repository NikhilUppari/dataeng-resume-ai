from __future__ import annotations

import tempfile
from pathlib import Path
from textwrap import wrap
from typing import Optional

from utils.docx_exporter import build_docx
from utils.schema import TailoredResume


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
PAGE_MARGIN = 54
BODY_FONT_SIZE = 10
HEADING_FONT_SIZE = 12
EDUCATION_HEADING_FONT_SIZE = 14
SUBHEADING_FONT_SIZE = 10
BODY_LINE_HEIGHT = 12
HEADING_SPACE_BEFORE = 6
HEADING_SPACE_AFTER = 2
SECTION_END_SPACE_AFTER = 4


def build_pdf(resume: TailoredResume) -> Optional[bytes]:
    """Build a PDF export for the tailored resume.

    Word/Pandoc conversion is used when available for highest fidelity. A
    built-in text PDF fallback keeps the PDF download available without local
    converter setup.
    """
    try:
        from docx2pdf import convert
    except Exception:
        convert = None

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        docx_path = temp_path / "tailored_resume.docx"
        pdf_path = temp_path / "tailored_resume.pdf"
        docx_path.write_bytes(build_docx(resume))

        if convert is not None:
            try:
                convert(str(docx_path), str(pdf_path))
                if pdf_path.exists():
                    return pdf_path.read_bytes()
            except Exception:
                pass

        try:
            import pypandoc

            pypandoc.convert_file(str(docx_path), "pdf", outputfile=str(pdf_path))
            if pdf_path.exists():
                return pdf_path.read_bytes()
        except Exception:
            pass
    return _build_fallback_pdf(resume)


def _build_fallback_pdf(resume: TailoredResume) -> bytes:
    lines = _resume_lines(resume)
    pages = _paginate(lines)
    return _write_pdf(pages)


def _resume_lines(resume: TailoredResume) -> list[dict[str, object]]:
    lines: list[dict[str, object]] = []

    def heading(text: str, *, size: int = HEADING_FONT_SIZE) -> None:
        lines.append({"text": text, "size": size, "bold": True, "before": HEADING_SPACE_BEFORE, "after": HEADING_SPACE_AFTER, "rule": True})

    def body(text: str, *, indent: int = 0, bold: bool = False, size: int = BODY_FONT_SIZE, after: int = 0) -> None:
        lines.append({"text": text, "size": size, "bold": bold, "indent": indent, "after": after})

    for index, detail in enumerate(resume.personal_details):
        body(detail, bold=(index == 0))

    heading("Professional Summary")
    for item in resume.summary:
        body(f"- {item}", indent=10)

    heading("Technical Skills")
    for category, values in resume.technical_skills.items():
        if values:
            body(f"{category}: {', '.join(values)}")

    heading("Professional Experience")
    for exp in resume.experiences:
        header = " | ".join(part for part in [exp.client_name, exp.title, exp.dates, exp.domain] if part)
        if header:
            body(header, bold=True, size=SUBHEADING_FONT_SIZE)
        for item in exp.responsibilities:
            body(f"- {item}", indent=10)
        if exp.environment:
            body(f"Environment: {', '.join(exp.environment)}", after=SECTION_END_SPACE_AFTER)

    if resume.certifications:
        heading("Certifications")
        for cert in resume.certifications:
            body(f"- {cert}", indent=10)

    if resume.education:
        heading("Education", size=EDUCATION_HEADING_FONT_SIZE)
        for line in resume.education.splitlines():
            if line.strip():
                body(line.strip())

    return lines


def _paginate(lines: list[dict[str, object]]) -> list[list[str]]:
    pages: list[list[str]] = [[]]
    y = PAGE_HEIGHT - PAGE_MARGIN
    max_width = PAGE_WIDTH - (PAGE_MARGIN * 2)

    for line in lines:
        size = int(line.get("size", BODY_FONT_SIZE))
        indent = int(line.get("indent", 0))
        before = int(line.get("before", 0))
        after = int(line.get("after", 0))
        line_height = max(BODY_LINE_HEIGHT, int(size * 1.25))
        wrapped = _wrap_pdf_text(str(line.get("text", "")), max_width - indent, size)
        needed = before + (len(wrapped) * line_height) + after
        if y - needed < PAGE_MARGIN and pages[-1]:
            pages.append([])
            y = PAGE_HEIGHT - PAGE_MARGIN

        y -= before
        for index, text in enumerate(wrapped):
            text_indent = indent if index == 0 else indent + 12
            pages[-1].append(_text_command(PAGE_MARGIN + text_indent, y, text, size, bool(line.get("bold"))))
            y -= line_height
        if line.get("rule"):
            rule_y = y + 3
            pages[-1].append(f"{PAGE_MARGIN} {rule_y:.2f} m {PAGE_WIDTH - PAGE_MARGIN} {rule_y:.2f} l S")
        y -= after

    return pages


def _wrap_pdf_text(text: str, width: int, font_size: int) -> list[str]:
    max_chars = max(24, int(width / (font_size * 0.52)))
    return wrap(" ".join(text.split()), width=max_chars, break_long_words=False) or [""]


def _text_command(x: int, y: int, text: str, size: int, bold: bool) -> str:
    font = "F2" if bold else "F1"
    return f"BT /{font} {size} Tf {x} {y:.2f} Td ({_escape_pdf_text(text)}) Tj ET"


def _escape_pdf_text(text: str) -> str:
    safe = text.encode("latin-1", errors="replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_pdf(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]
    page_refs: list[str] = []
    for page in pages:
        content = "\n".join(page).encode("latin-1", errors="replace")
        content_obj = len(objects) + 2
        page_obj = len(objects) + 1
        page_refs.append(f"{page_obj} 0 R")
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_obj} 0 R >>"
            ).encode("ascii")
        )
        objects.append(b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream")

    objects[1] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>".encode("ascii")

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)
