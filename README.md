# Resume Analyzer

A private Flask web app for reviewing resumes, comparing a resume with a job description, drafting cover letters, and using focused writing tools. The app runs locally or as a Python web service on Render.

## Features

- Resume analysis for PDF and TXT files
- Existing heuristic resume score, text-based ATS checks, resume statistics, and AI feedback
- Resume-to-job-description match review and optional simple keyword overlap
- Cover-letter drafts in five tones
- Action verb, achievement wording, bullet point, section order, and interview preparation tools
- In-session analysis history and comparison
- Gemini model fallback from `gemini-3.8-flash` to `gemini-3.5-flash-lite`

The resume score and ATS checks are product heuristics. They do not simulate an employer's ATS or predict hiring outcomes.

## Run locally

Requirements: Python 3.11 or later and a Gemini API key.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
py main.py
```

Open `http://127.0.0.1:5000`.

Set these values in `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
APP_PASSWORD=choose_a_long_private_workspace_password
FLASK_SECRET_KEY=replace_with_a_random_secret
```

`APP_PASSWORD` enables the shared-password sign-in gate locally. `FLASK_SECRET_KEY` signs the session cookie; keep it secret and use a different value in each environment. Never commit `.env` or put API keys in source files.

## Deploy to Render

The repository includes [`render.yaml`](render.yaml) for a Python web service. Render builds with `pip install -r requirements.txt` and runs Flask with Gunicorn.

1. Push this repository to a Git provider and connect it in Render.
2. Create a Blueprint from the repository so Render reads `render.yaml`.
3. If you already created a Render web service manually, update its Start Command under **Settings → Build & Deploy** to `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`; otherwise it may keep using an old Streamlit command.
4. When prompted, enter `GEMINI_API_KEY` and a strong `APP_PASSWORD`. Keep both in Render's environment settings.
5. Render generates `FLASK_SECRET_KEY` from the Blueprint configuration.
6. Wait for the service health check at `/health` and open its Render URL.

The Render configuration selects the free web-service plan. Gemini API usage is separate and may incur charges. The shared password restricts access, while each browser session is limited to three resume analyses, three job matches, and three cover-letter generations. These session limits are suitable for a small private workspace; they are not a substitute for account-based quotas on a public multi-user product.

## Data handling

- Resume uploads accept PDF and TXT files up to 20 MB. The request cap includes multipart form overhead.
- Resume text and job descriptions are sent from the server to the configured Google Gemini API when the user requests AI feedback.
- This project has no database or resume library. It does not intentionally persist uploads or reports; analysis history stays in the open browser tab and disappears when it is refreshed or closed.
- The app does not log resume content. Do not upload sensitive information unless you are comfortable with the configured Gemini provider's data handling terms.
- Use Render environment variables for secrets. Do not commit `.env` or share `GEMINI_API_KEY`.

## Project structure

```text
app.py                 Flask routes, sign-in, CSRF, session quotas
resume_service.py      PDF/TXT parsing, existing scoring and Gemini workflows
main.py                Local development entry point
templates/             Flask HTML templates
static/                Responsive CSS and browser interactions
render.yaml            Render Blueprint configuration
requirements.txt       Render and local Python dependencies
```
