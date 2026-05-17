# Run Locally

This guide shows how to run `dataeng-resume-ai` after downloading or cloning the repository.

## Prerequisites

Install these first:

- Python 3.10 or newer
- Git
- PowerShell, Windows Terminal, or another terminal
- Optional: Microsoft Word for best DOCX-to-PDF export on Windows. If Word/Pandoc is unavailable, the app uses a built-in PDF fallback.
- Optional: Ollama for local AI enrichment

The app still works without Ollama by using deterministic local tailoring logic.

## 1. Clone the Repository

```powershell
git clone https://github.com/NikhilUppari/dataeng-resume-ai.git
cd dataeng-resume-ai
```

If you already downloaded the ZIP from GitHub, extract it and open a terminal inside the extracted `dataeng-resume-ai` folder.

## 2. Create a Virtual Environment

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If activation is blocked, allow local script execution for your user account:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate the virtual environment again.

## 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

## 4. Optional Ollama Setup

Install Ollama from:

```text
https://ollama.com
```

Pull at least one supported local model:

```powershell
ollama pull llama3.1
```

Other supported models:

```powershell
ollama pull qwen2.5
ollama pull mistral
ollama pull deepseek-r1
```

Confirm Ollama is running:

```powershell
ollama list
```

## 5. Run the App

From the repository root with the virtual environment activated:

```powershell
streamlit run app.py
```

If `streamlit` is not recognized, run it through the virtual environment executable:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

Streamlit will print a local URL, usually:

```text
http://localhost:8501
```

Open that URL in your browser.

## 6. Use the App

1. Upload a resume as DOCX, PDF, or TXT.
2. Paste the target Data Engineering job description.
3. Review detected client experiences.
4. Choose AWS, Azure, or GCP for each client.
5. Generate the tailored resume.
6. Review ATS scores and keyword gaps.
7. Download the DOCX output.
8. Download the PDF output if local PDF conversion is available.

## Troubleshooting

If dependencies fail to install, confirm the virtual environment is active and retry:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If the app says Ollama is unavailable, confirm the Ollama desktop app or service is running:

```powershell
ollama list
```

If Word/Pandoc PDF conversion is unavailable, the app uses a built-in fallback PDF export. DOCX remains the highest-fidelity editable output.

If resume parsing is incomplete, try uploading a cleaner DOCX or TXT version. Highly formatted PDFs can be harder to parse reliably.
