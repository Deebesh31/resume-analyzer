# ResuMate

ResuMate is a Flask web app for reviewing resumes, comparing a resume with a job description, drafting cover letters, and using focused writing tools. It runs locally or as a Python web service on Render.

## Features

- Resume analysis for PDF, DOCX, and TXT files
- Document extraction review with entity extraction, section headings, date ranges, and layout warnings
- Resume-to-job-description comparison with recognized skill phrases, priority weighting, and matching text evidence
- Descriptive resume statistics and actionable written feedback
- Cover-letter drafts in five tones
- Action verb, achievement wording, bullet point, section order, and interview preparation tools
- In-session analysis history and comparison
- Google account menu with live remaining usage for the current session
- Google Gemini model fallback from `gemini-3.8-flash` to `gemini-3.5-flash-lite`

ResuMate does not produce a general resume score or simulate an employer's applicant tracking system. Skill coverage is calculated only from a maintained list of recognized phrases in the pasted job description; it is not a hiring prediction or a complete interpretation of every requirement. Text extraction, entity labels, and layout warnings are best-effort checks and can miss content or formatting problems. Scanned PDFs without selectable text are not supported; export them as a text-based PDF or DOCX first.

## Set up Auth0 sign-in

The app uses Auth0 Universal Login for Google sign-in. Create an Auth0 **Regular Web Application** and enable the `google-oauth2` social connection for that application. The app only accepts Google identities with verified email addresses.

In the Auth0 application's settings, add these local URLs:

- Allowed Callback URL: `http://127.0.0.1:5000/auth/callback`
- Allowed Logout URL: `http://127.0.0.1:5000/login`
- Allowed Web Origin: `http://127.0.0.1:5000`

Auth0's built-in Google credentials are suitable for initial testing. Before opening the app to real users, configure your own Google OAuth credentials in Auth0.

The app favicon is served at `/static/favicon.svg`. To show it in Auth0's hosted Universal Login browser tab, after deploying, use the Auth0 Management API to `PATCH https://<your-auth0-domain>/api/v2/branding` with `{"favicon_url":"https://<your-service>.onrender.com/static/favicon.svg"}` and a token with the `update:branding` scope. Auth0 currently exposes the hosted-login favicon through this Branding API setting.

## Run locally

Requirements: Python 3.11 or later, a Gemini API key, and an Auth0 application configured as above.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set these values in `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
FLASK_SECRET_KEY=replace_with_a_random_secret
AUTH0_DOMAIN=your-tenant.region.auth0.com
AUTH0_CLIENT_ID=your_auth0_application_client_id
AUTH0_CLIENT_SECRET=your_auth0_application_client_secret
AUTH0_CALLBACK_URL=http://127.0.0.1:5000/auth/callback
AUTH0_LOGOUT_RETURN_URL=http://127.0.0.1:5000/login
```

`AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, and `AUTH0_CLIENT_SECRET` come from the Auth0 application settings. `AUTH0_CALLBACK_URL` and `AUTH0_LOGOUT_RETURN_URL` must exactly match the URLs allowed in Auth0. `FLASK_SECRET_KEY` signs the session cookie; keep it secret and use a different value in each environment. Never commit `.env` or put secrets in source files.

After saving `.env`, start the app with `py main.py`, then open `http://127.0.0.1:5000`.

## Deploy to Render

The repository includes [`render.yaml`](render.yaml) for a Python web service. Render builds with `pip install -r requirements.txt` and runs Flask with Gunicorn.

1. Push this repository to a Git provider and connect it in Render.
2. Create a Blueprint from the repository so Render reads `render.yaml`.
3. If you already created a Render web service manually, update its Start Command under **Settings → Build & Deploy** to `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`; otherwise it may keep using an old Streamlit command.
4. Add `GEMINI_API_KEY`, `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, and `AUTH0_CLIENT_SECRET` in Render's environment settings. Keep secrets private.
5. Set `AUTH0_CALLBACK_URL` to `https://<your-service>.onrender.com/auth/callback` and `AUTH0_LOGOUT_RETURN_URL` to `https://<your-service>.onrender.com/login`.
6. Add those exact callback and logout URLs, plus `https://<your-service>.onrender.com` as an Allowed Web Origin, to the Auth0 application settings. Use your custom domain if you have one.
7. Render generates `FLASK_SECRET_KEY` from the Blueprint configuration. If the service still has the old `APP_PASSWORD` variable, remove it; this app no longer uses it.
8. Wait for the service health check at `/health` and open its Render URL.

The Render configuration selects the free web-service plan. Google Gemini usage is separate and may incur charges. Each authenticated browser session is limited to three resume analyses, three job matches, and three cover-letter generations. These session limits are suitable for a small project; they are not a substitute for account-based quotas on a public multi-user product.

## Data handling

- Resume uploads accept PDF, DOCX, and TXT files up to 20 MB. The request cap includes multipart form overhead.
- PDF parsing uses PyMuPDF and DOCX parsing uses python-docx. PDF text is ordered using page coordinates and a column-aware reading-order heuristic. A local English token-classification model identifies likely names, contact details, titles, employers, qualifications, institutions, skills, certifications, and languages. Its quantized ONNX weights and tokenizer are downloaded lazily from Hugging Face on the first parse and cached by the service. Resume text is processed locally by this parser; it is not sent to Hugging Face. If the model cannot be loaded, ResuMate falls back to basic contact and section checks and shows a notice. Scanned PDFs still require OCR before upload; columns, tables, header/footer content, and image text can be misread.
- Job matching compares a curated list of skill phrases with the extracted resume text. Required phrases count 3, unprioritized phrases 2, and preferred phrases 1; the coverage percentage applies only to recognized phrases. An optional job-title check is exact-phrase only. Education checks compare degree level but not field of study, and years-of-experience requirements are surfaced for manual comparison. The report shows evidence excerpts so the user can check each match. Terms outside the current phrase list are not included in that percentage.
- Research basis: [Yu et al. (ACL 2005)](https://aclanthology.org/P05-1062/) segment resumes before extracting detailed fields; [Wei et al. (SIGIR 2020)](https://arxiv.org/abs/2005.11017) show how document layout cues can improve extraction; and [Retyk et al. (HR@RecSys 2023)](https://arxiv.org/abs/2309.07015) study joint section/line and entity/token labeling. ResuMate applies these ideas as coordinate-based PDF reading order, rule-based section headings, and token-level entity extraction; it does not reproduce the full research architectures. The Retyk paper's public companion repository contains feature descriptions, not a ready-to-run trained parser. The [resume NER checkpoint](https://huggingface.co/oksomu/resume-ner) used here is a separate community model licensed under Apache 2.0, pinned in [resume_parser.py](resume_parser.py) to a specific revision. Its model-card benchmark is not an independent evaluation of ResuMate. Before making accuracy claims, evaluate it against a consented, representative set of resumes from the intended users.
- Resume text and job descriptions are sent from the server to the configured Google Gemini service when the user requests a review.
- This project has no database or resume library. It does not intentionally persist uploads or reports; analysis history stays in the open browser tab and disappears when it is refreshed or closed.
- The app does not log resume content. Do not upload sensitive information unless you are comfortable with the configured Gemini provider's data handling terms.
- Use Render environment variables for secrets. Do not commit `.env` or share `GEMINI_API_KEY`.

## Project structure

```text
app.py                 Flask routes, sign-in, CSRF, session quotas
resume_service.py      PDF/DOCX/TXT extraction, layout checks, requirement matching, and Google Gemini workflows
resume_parser.py       Local resume entity extraction with a pinned quantized ONNX model
main.py                Local development entry point
templates/             Flask HTML templates
static/                Responsive CSS and browser interactions
render.yaml            Render Blueprint configuration
requirements.txt       Render and local Python dependencies
```
