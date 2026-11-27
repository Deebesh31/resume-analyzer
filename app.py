"""Flask web application for the Resume Analyzer."""

import hmac
import os
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    get_flashed_messages,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from resume_service import (
    ANALYSIS_MODES,
    FOCUS_AREAS,
    TOOLS,
    GeminiConfigurationError,
    analyze_job_match,
    analyze_resume,
    generate_cover_letter,
    generate_tool_output,
)


load_dotenv()

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_REQUEST_BYTES = 22 * 1024 * 1024  # Leave room for multipart form fields and boundaries.
MAX_FEATURE_REQUESTS = 3
USAGE_FEATURES = ("resume_analysis", "job_match", "cover_letter")
IS_RENDER = os.getenv("RENDER", "").lower() == "true"
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "").strip().removeprefix("https://").rstrip("/")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "").strip()
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "").strip()
AUTH0_CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL", "").strip()
AUTH0_LOGOUT_RETURN_URL = os.getenv("AUTH0_LOGOUT_RETURN_URL", "").strip()
AUTH0_CONFIGURED = all((
    AUTH0_DOMAIN,
    AUTH0_CLIENT_ID,
    AUTH0_CLIENT_SECRET,
    AUTH0_CALLBACK_URL,
    AUTH0_LOGOUT_RETURN_URL,
))

if IS_RENDER and not AUTH0_CONFIGURED:
    raise RuntimeError(
        "Set AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_CALLBACK_URL, "
        "and AUTH0_LOGOUT_RETURN_URL in Render's environment before starting the service."
    )

app = Flask(__name__)
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "")
if IS_RENDER and not FLASK_SECRET_KEY:
    raise RuntimeError("Set FLASK_SECRET_KEY in Render's environment before starting the service.")

app.config.update(
    SECRET_KEY=FLASK_SECRET_KEY or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=IS_RENDER,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
)
oauth = OAuth(app)
if AUTH0_CONFIGURED:
    oauth.register(
        name="auth0",
        client_id=AUTH0_CLIENT_ID,
        client_secret=AUTH0_CLIENT_SECRET,
        server_metadata_url=f"https://{AUTH0_DOMAIN}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile email"},
    )
auth0 = oauth.create_client("auth0") if AUTH0_CONFIGURED else None


def ensure_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def api_error(message, status):
    return jsonify({"error": message}), status


@app.before_request
def protect_routes_and_posts():
    public_endpoints = {
        "health", "login", "login_google", "auth0_callback", "static",
    }
    if request.endpoint not in public_endpoints and not session.get("auth_user"):
        if request.path.startswith("/api/"):
            return api_error("Sign in to continue.", 401)
        return redirect(url_for("login"))

    if request.method == "POST":
        expected = session.get("csrf_token", "")
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("_csrf", "")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            if request.path.startswith("/api/"):
                return api_error("The request could not be verified. Refresh the page and try again.", 400)
            abort(400)


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'",
    )
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.context_processor
def inject_auth_user():
    return {"auth_user": session.get("auth_user")}


def consume_feature_request(feature):
    usage = session.get("usage", {})
    current = int(usage.get(feature, 0))
    if current >= MAX_FEATURE_REQUESTS:
        raise PermissionError(
            f"This session has used all {MAX_FEATURE_REQUESTS} requests for this feature."
        )
    usage[feature] = current + 1
    session["usage"] = usage
    session.modified = True


def remaining_usage():
    usage = session.get("usage", {})
    return {
        feature: max(0, MAX_FEATURE_REQUESTS - int(usage.get(feature, 0)))
        for feature in USAGE_FEATURES
    }


def get_resume_upload(field_name="resume"):
    uploaded = request.files.get(field_name)
    if uploaded is None or not uploaded.filename:
        raise ValueError("Choose a PDF or TXT resume to continue.")
    filename = secure_filename(uploaded.filename)
    if not filename or os.path.splitext(filename)[1].lower() not in (".pdf", ".txt"):
        raise ValueError("Unsupported file format. Upload a PDF or TXT file.")
    file_bytes = uploaded.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("The resume exceeds the 20 MB file limit.")
    return filename, file_bytes


def parse_bool(name, default=False):
    values = request.form.getlist(name)
    if not values:
        return default
    value = values[-1]
    return value.lower() in ("1", "true", "on", "yes")


def run_api_operation(operation):
    try:
        return jsonify(operation())
    except ValueError as error:
        return api_error(str(error), 400)
    except PermissionError as error:
        return api_error(str(error), 429)
    except GeminiConfigurationError as error:
        return api_error(str(error), 503)
    except Exception:
        # Avoid returning prompts, resume text, credentials, or internal traces to the browser.
        app.logger.exception("A resume analysis request failed.")
        return api_error("The analysis could not be completed. Check the API settings and try again.", 502)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/login")
def login():
    if session.get("auth_user"):
        return redirect(url_for("index"))
    return render_template(
        "login.html",
        csrf_token=ensure_csrf_token(),
        auth0_configured=AUTH0_CONFIGURED,
        errors=get_flashed_messages(),
    )


@app.get("/login/google")
def login_google():
    if not auth0:
        flash("Sign-in is not configured yet. Add the Auth0 settings before continuing.", "error")
        return redirect(url_for("login"))
    return auth0.authorize_redirect(AUTH0_CALLBACK_URL, connection="google-oauth2")


@app.get("/auth/callback")
def auth0_callback():
    if not auth0:
        flash("Sign-in is not configured yet. Add the Auth0 settings before continuing.", "error")
        return redirect(url_for("login"))
    try:
        token = auth0.authorize_access_token()
        userinfo = token.get("userinfo") or {}
        subject = userinfo.get("sub", "")
        if not subject.startswith("google-oauth2|"):
            raise ValueError("Only Google sign-in is accepted.")
        if not userinfo.get("email") or userinfo.get("email_verified") is not True:
            raise ValueError("Auth0 did not return a verified email address.")
        session.clear()
        session["auth_user"] = {
            "sub": subject,
            "email": userinfo["email"],
            "name": userinfo.get("name") or userinfo["email"],
        }
        session["usage"] = {}
        session.permanent = True
        ensure_csrf_token()
        return redirect(url_for("index"))
    except Exception as error:
        app.logger.warning("Auth0 callback failed (%s).", type(error).__name__)
        session.clear()
        ensure_csrf_token()
        flash("We couldn't verify your sign-in. Please try again.", "error")
        return redirect(url_for("login"))


@app.post("/logout")
def logout():
    session.clear()
    ensure_csrf_token()
    if not AUTH0_CONFIGURED:
        return redirect(url_for("login"))
    params = urlencode({
        "client_id": AUTH0_CLIENT_ID,
        "returnTo": AUTH0_LOGOUT_RETURN_URL,
    })
    return redirect(f"https://{AUTH0_DOMAIN}/v2/logout?{params}")


@app.get("/")
def index():
    session.permanent = True
    return render_template(
        "index.html",
        csrf_token=ensure_csrf_token(),
        usage=remaining_usage(),
        analysis_modes=ANALYSIS_MODES,
        focus_areas=FOCUS_AREAS,
        tools=TOOLS,
    )


@app.post("/api/analyze")
def api_analyze():
    def operation():
        filename, file_bytes = get_resume_upload()
        consume_feature_request("resume_analysis")
        focus_areas = request.form.getlist("focus_areas")
        focus_areas = [item for item in focus_areas if item in FOCUS_AREAS]
        result = analyze_resume(
            filename,
            file_bytes,
            analysis_mode=request.form.get("analysis_mode", "Standard Analysis"),
            focus_areas=focus_areas,
            job_role=request.form.get("job_role", "").strip(),
            enable_scoring=parse_bool("enable_scoring", True),
            enable_statistics=parse_bool("enable_statistics", True),
            enable_ats_check=parse_bool("enable_ats_check", True),
            enable_action_verbs=parse_bool("enable_action_verbs", False),
        )
        result["remaining_usage"] = remaining_usage()
        return result
    return run_api_operation(operation)


@app.post("/api/job-match")
def api_job_match():
    def operation():
        filename, file_bytes = get_resume_upload()
        job_description = request.form.get("job_description", "")
        if not job_description.strip():
            raise ValueError("Paste a job description to continue.")
        consume_feature_request("job_match")
        result = analyze_job_match(
            filename,
            file_bytes,
            job_description,
            include_keywords=parse_bool("include_keywords", False),
        )
        result["remaining_usage"] = remaining_usage()
        return result
    return run_api_operation(operation)


@app.post("/api/cover-letter")
def api_cover_letter():
    def operation():
        filename, file_bytes = get_resume_upload()
        job_description = request.form.get("job_description", "")
        if not job_description.strip():
            raise ValueError("Add the job description so the draft has role context.")
        tone = request.form.get("tone", "Professional")
        allowed_tones = ("Professional", "Enthusiastic", "Formal", "Creative", "Conversational")
        if tone not in allowed_tones:
            tone = "Professional"
        consume_feature_request("cover_letter")
        letter = generate_cover_letter(
            filename,
            file_bytes,
            job_description,
            company=request.form.get("company", "").strip(),
            role=request.form.get("role", "").strip(),
            tone=tone,
        )
        return {"cover_letter": letter, "remaining_usage": remaining_usage()}
    return run_api_operation(operation)


@app.post("/api/tools")
def api_tools():
    def operation():
        tool_name = request.form.get("tool_name", "")
        file_name = None
        file_bytes = None
        text = request.form.get("tool_text", "")
        if tool_name == "Interview Question Generator":
            file_name, file_bytes = get_resume_upload("interview_resume")
        output = generate_tool_output(
            tool_name,
            text,
            file_name=file_name,
            file_bytes=file_bytes,
            target_industry=request.form.get("target_industry", "").strip(),
            target_role=request.form.get("target_role", "").strip(),
        )
        return {"output": output}
    return run_api_operation(operation)


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    return api_error("The request exceeds the 22 MB upload limit.", 413)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
