from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from utils.docx_exporter import build_docx
from utils.schema import TailoredResume


def build_pdf(resume: TailoredResume) -> Optional[bytes]:
    """Best-effort DOCX to PDF conversion.

    On Windows, docx2pdf uses Microsoft Word. If Word is unavailable, the app
    gracefully disables PDF download while keeping DOCX export available.
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
            return None
    return None
