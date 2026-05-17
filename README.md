# dataeng-resume-ai

Production-style local AI resume tailoring app for real Data Engineering job applications.

The app runs on your laptop with Streamlit and Ollama. It parses a DOCX or PDF resume, analyzes a pasted job description, lets you choose AWS/Azure/GCP for each client experience, and generates an ATS-friendly tailored resume with DOCX and best-effort PDF export.

## Features

- Local resume upload for DOCX, PDF, and TXT
- Job description analyzer for required skills, preferred skills, tools, domains, responsibilities, certifications, and seniority
- Per-client cloud selection for AWS, Azure, or GCP
- Domain-aware generation for healthcare, finance/banking, retail/e-commerce, aviation, and travel
- Truthful domain strategy that avoids unsupported domain claims and uses adjacent platform positioning when the JD domain has no matching resume client
- Known client mapping for Oak Street Health, HCA Healthcare, Northern Trust, eBay, United Airlines, and MakeMyTrip
- Timeline validation to avoid placing newer tools into older experience periods
- Tailored professional summary, technical skills, responsibilities, and environment sections
- Personal header/contact details preserved at the beginning of generated resumes
- Format-controlled client responsibilities with target counts by experience order and compact 29-33 word bullets
- ATS analysis panel with match score, matched keywords, missing keywords, missing tools, cloud score, domain score, and suggestions
- ATS-friendly DOCX export through `python-docx` with Calibri 10pt body text, 12pt Camel Case section headings, thin heading borders, and compact capped technical skills lines
- PDF export through `docx2pdf` on Windows or `pypandoc` when configured, with a built-in fallback PDF writer
- Optional local Ollama enrichment with `llama3.1`, `qwen2.5`, `mistral`, or `deepseek-r1`
- Deterministic fallback generation when Ollama is not running

## Project Structure

```text
dataeng-resume-ai/
  app.py
  requirements.txt
  README.md
  prompts/
  services/
  utils/
  outputs/
  sample_data/
  templates/
  parsers/
  generators/
```

## Installation

```powershell
cd dataeng-resume-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ollama Setup

Install Ollama from:

```text
https://ollama.com
```

Pull at least one local model:

```powershell
ollama pull llama3.1
ollama pull qwen2.5
ollama pull mistral
ollama pull deepseek-r1
```

Confirm Ollama is running:

```powershell
ollama list
```

The app still works without Ollama by using local deterministic tailoring logic.

## Run

```powershell
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

For a full local setup walkthrough, see [docs/user_guides/run_locally.md](docs/user_guides/run_locally.md).

## Sample Usage

1. Upload your existing resume as DOCX or PDF.
2. Paste a target Data Engineering job description.
3. Select AWS, Azure, or GCP for each client experience.
4. Choose an Ollama model if Ollama is running.
5. Generate the tailored resume.
6. Review the ATS panel and keyword gaps.
7. Download DOCX, and PDF when your local PDF converter is available.

## Screenshots

Add screenshots after running locally:

```text
docs/screenshots/upload-and-jd.png
docs/screenshots/cloud-selection.png
docs/screenshots/ats-panel.png
docs/screenshots/resume-preview.png
```

## Notes on Format Preservation

The app preserves client names, dates, experience order, and section intent. DOCX export uses an ATS-friendly professional resume layout generated locally with `python-docx`.

Current DOCX formatting rules:

- Body text uses Calibri 10pt.
- Section headings use Camel Case, Calibri 12pt, bold text, 6pt before spacing, 2pt after spacing, and a thin bottom border.
- Client names and subheadings use Calibri 10pt.
- Education stays at the bottom; the Education heading uses Calibri 14pt and education details use Calibri 10pt.
- Technical skills render as compact category lines, such as `Cloud Platforms: AWS, Azure, S3, Glue, Redshift`.
- Technical skills are capped by category to avoid keyword stuffing.
- Client experience headers render on one compact line: `Client Name | Role | Dates | Domain`.
- Responsibility bullets use tight spacing and bold known technical tools that appear in the bullet.
- Client responsibility counts target 27 points for the current client, then 25, 23, 20, and 10 for older clients.

Exact visual preservation of complex original DOCX formatting can be improved by adding template-specific replacement rules in `templates/`.

## Notes on Truthful Domain Tailoring

The app now compares the JD domain with the resume's detected client domains before generating tailored experience bullets.

- If the JD domain matches a resume client domain, the app can directly align that client's responsibilities to the JD.
- If the JD domain does not match any resume client domain, the app uses adjacent-fit positioning instead of pretending direct domain experience.
- For telecom mediation JDs without telecom client history, the app emphasizes transferable streaming, distributed systems, platform engineering, observability, and SRE experience.
- Unsupported telecom claims such as direct ASN.1 decoding, CDR/UDR processing, OSS/BSS mediation ownership, and vendor platform work are not injected unless they already exist in the source resume.
- The ATS panel shows a domain-gap warning when adjacent-fit positioning is used.

## Future Improvements

- Template-aware DOCX replacement for exact formatting preservation
- SQLite application history for generated versions
- Side-by-side diff against original resume
- More granular timeline rules by cloud service release date
- Resume truthfulness checklist before export
- Local embeddings for richer JD-to-resume keyword matching
- Optional portfolio mode with anonymized sample outputs
