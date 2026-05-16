# dataeng-resume-ai

Production-style local AI resume tailoring app for real Data Engineering job applications.

The app runs on your laptop with Streamlit and Ollama. It parses a DOCX or PDF resume, analyzes a pasted job description, lets you choose AWS/Azure/GCP for each client experience, and generates an ATS-friendly tailored resume with DOCX and best-effort PDF export.

## Features

- Local resume upload for DOCX, PDF, and TXT
- Job description analyzer for required skills, preferred skills, tools, domains, responsibilities, certifications, and seniority
- Per-client cloud selection for AWS, Azure, or GCP
- Domain-aware generation for healthcare, finance/banking, retail/e-commerce, aviation, and travel
- Known client mapping for Oak Street Health, HCA Healthcare, Northern Trust, eBay, United Airlines, and MakeMyTrip
- Timeline validation to avoid placing newer tools into older experience periods
- Tailored professional summary, technical skills, responsibilities, and environment sections
- Format-controlled client responsibilities with target counts by experience order and compact 29-33 word bullets
- ATS analysis panel with match score, matched keywords, missing keywords, missing tools, cloud score, domain score, and suggestions
- ATS-friendly DOCX export through `python-docx` with Calibri 10pt body text, Title Case section headings, thin heading borders, and compact technical skills lines
- PDF export through `docx2pdf` on Windows or `pypandoc` when configured
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
- Section headings use Title Case, Calibri 12pt, bold text, and a thin bottom border.
- Technical skills render as compact category lines, such as `Cloud Platforms: AWS, Azure, S3, Glue, Redshift`.
- Client experience headers render on one compact line: `Client: Client Name | Role | Dates | Domain`.
- Responsibility bullets use tight spacing and bold known technical tools that appear in the bullet.
- Client responsibility counts target 28 points for the current client, then 25, 23, 20, and 18 for older clients.

Exact visual preservation of complex original DOCX formatting can be improved by adding template-specific replacement rules in `templates/`.

## Future Improvements

- Template-aware DOCX replacement for exact formatting preservation
- SQLite application history for generated versions
- Side-by-side diff against original resume
- More granular timeline rules by cloud service release date
- Resume truthfulness checklist before export
- Local embeddings for richer JD-to-resume keyword matching
- Optional portfolio mode with anonymized sample outputs
