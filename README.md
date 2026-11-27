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

The Render configuration selects the free web-service plan. Gemini API usage is separate and may incur charges. Each authenticated browser session is limited to three resume analyses, three job matches, and three cover-letter generations. These session limits are suitable for a small private workspace; they are not a substitute for account-based quotas on a public multi-user product.

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
