# Local Setup and Usage Guide

## Requirements

Before running this project locally, make sure your computer has:

- Python 3.10 or newer
- Git
- PowerShell or another terminal
- A local clone of this repository
- Internet access for the first dependency install
- Microsoft Word on Windows if you want the best DOCX-to-PDF export through `docx2pdf`
- Optional: Ollama for local AI enrichment

Python packages are installed from:

```text
requirements.txt
```

The current app dependencies are:

- `streamlit`
- `python-docx`
- `pdfplumber`
- `requests`
- `pypandoc`
- `docx2pdf` on Windows

Optional local Ollama models:

- `llama3.1`
- `qwen2.5`
- `mistral`
- `deepseek-r1`

The app can still run without Ollama. When Ollama is not detected, it uses deterministic local resume-tailoring logic.

## What This App Does

`dataeng-resume-ai` is a local resume tailoring tool for Data Engineering applications. It lets you upload a resume, paste a job description, choose cloud platforms for each client experience, and generate an ATS-friendly tailored resume.

Supported resume upload formats:

- DOCX
- PDF
- TXT

Generated output formats:

- DOCX
- PDF when your local PDF conversion setup is available

## Generated Resume Formatting

The DOCX output is generated with a compact ATS-friendly layout:

- Body text uses Calibri 10pt.
- Section headings use Title Case, Calibri 12pt, bold text, and a thin bottom border.
- Technical skills are written as compact category lines, such as `Cloud Platforms: AWS, Azure, S3, Glue, Redshift`.
- Each client header is kept on one line when data is available: `Client: Client Name | Role | Dates | Domain`.
- Client responsibility counts target 28 points for the current client, then 25, 23, 20, and 18 for older clients.
- Responsibility bullets target 29-33 words and bold known technical tools, skills, and platforms when they appear in the bullet.
- Bullets use tight spacing to keep long experience sections readable without adding unnecessary pages.

## First-Time Setup

Open PowerShell in the project folder:

```powershell
cd dataeng-resume-ai
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

If PowerShell blocks virtual environment activation, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate the virtual environment again.

## Optional Ollama Setup

Install Ollama from:

```text
https://ollama.com
```

Pull at least one supported model:

```powershell
ollama pull llama3.1
```

You can also pull the other supported models:

```powershell
ollama pull qwen2.5
ollama pull mistral
ollama pull deepseek-r1
```

Confirm Ollama is available:

```powershell
ollama list
```

If Ollama is running, the app will show `Ollama connected` in the sidebar.

## Running the App

From the project root with the virtual environment activated:

```powershell
streamlit run app.py
```

Streamlit will print a local URL in the terminal. Open that URL in your browser.

It usually looks like:

```text
http://localhost:8501
```

## Using the App

1. Upload your existing resume as a DOCX, PDF, or TXT file.
2. Paste the target job description into the job description box.
3. Review the detected client experiences.
4. Choose AWS, Azure, or GCP for each client experience.
5. If Ollama is connected, choose a model and decide whether to use local AI enrichment.
6. Click `Generate tailored resume`.
7. Review the ATS scores, matched keywords, missing keywords, missing tools, and suggestions.
8. Review the generated resume preview.
9. Download the DOCX output.
10. Download the PDF output if PDF export is available on your machine.

## Sample Data

Safe demo files live in:

```text
sample_data/
```

These files are intended to be committed and shared publicly. Use them for demos, screenshots, and testing workflows that should not expose private information.

## Private Data Rules

Real resumes, real job descriptions, generated resumes, and private notes should stay local.

Use these local-only folders for private files:

```text
personal_data/
private_data/
private_resumes/
local_resumes/
job_descriptions/
```

Generated output folders are also ignored:

```text
outputs/
exports/
generated_resumes/
```

The repository keeps this placeholder tracked:

```text
outputs/.gitkeep
```

That keeps the `outputs` folder available in a fresh clone while ignoring generated files inside it.

Before committing, check what Git can see:

```powershell
git status --short
```

If a real resume, real job description, generated DOCX, generated PDF, or private note appears in `git status`, do not commit it. Move it into an ignored private folder or rename it with one of the ignored private/generated filename patterns.

Ignored private/generated filename patterns include:

```text
*.local.docx
*.local.pdf
*.private.docx
*.private.pdf
*.generated.docx
*.generated.pdf
*.tailored.docx
*.tailored.pdf
```

## Recommended Local Workflow

Keep the public repo clean:

```text
sample_data/      safe demo inputs
docs/             public documentation
outputs/.gitkeep  tracked folder placeholder
```

Keep private work local:

```text
personal_data/       real resumes and notes
job_descriptions/    real job descriptions
outputs/             generated files
exports/             exported files
generated_resumes/   generated resume versions
```

Before pushing to GitHub:

```powershell
git status --short
```

Only commit source code, documentation, safe sample data, and placeholders.

## Troubleshooting

If `streamlit` is not recognized, activate the virtual environment and install dependencies again:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If Ollama is not detected, confirm the Ollama app or service is running:

```powershell
ollama list
```

If PDF export is disabled, download the DOCX output instead. PDF export depends on local tools such as Microsoft Word with `docx2pdf` on Windows or a working Pandoc PDF toolchain.

If resume parsing looks incomplete, try uploading a cleaner DOCX or TXT version of the resume. Highly formatted PDFs can be harder to parse reliably.

If generated content looks too broad, paste a more complete job description and make sure each client has the correct cloud selected before generating.
