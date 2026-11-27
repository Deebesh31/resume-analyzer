"""Flask web application for ResuMate."""

import hmac
import ipaddress
import os
import secrets
import time
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
from usage_store import TrialLimitExceeded, UsageStore

from resume_service import (
    ANALYSIS_MODES,
    FOCUS_AREAS,
    TOOLS,
    AffindaParserError,
    OpenAIConfigurationError,
    analyze_job_match,
    analyze_resume,
    generate_cover_letter,
    generate_tool_output,
    reset_request_deadline,
    set_request_deadline,
)


load_dotenv()

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_REQUEST_BYTES = 22 * 1024 * 1024  # Leave room for multipart form fields and boundaries.
MAX_FEATURE_REQUESTS = 3
MAX_JOB_DESCRIPTION_CHARS = 12_000
MAX_TOOL_TEXT_CHARS = 8_000
MAX_CONTEXT_FIELD_CHARS = 160
USAGE_LIMITS = {
    "resume_analysis": MAX_FEATURE_REQUESTS,
    "job_match": MAX_FEATURE_REQUESTS,
    "cover_letter": MAX_FEATURE_REQUESTS,
    "resume_tools": MAX_FEATURE_REQUESTS,
}
USAGE_FEATURES = tuple(USAGE_LIMITS)
IS_RENDER = os.getenv("RENDER", "").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "").strip()


def env_positive_int(name, default):
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as error:
        raise RuntimeError(f"{name} must be a positive integer.") from error
    if value < 1:
        raise RuntimeError(f"{name} must be a positive integer.")
    return value


def env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


TRIAL_SIGNUPS_ENABLED = env_bool("TRIAL_SIGNUPS_ENABLED", True)
TRIAL_ALLOWED_EMAILS = {
    item.strip().lower()
    for item in os.getenv("TRIAL_ALLOWED_EMAILS", "").split(",")
    if item.strip()
}
TRIAL_ACCOUNT_REQUESTS_PER_HOUR = env_positive_int("TRIAL_ACCOUNT_REQUESTS_PER_HOUR", 6)
TRIAL_IP_REQUESTS_PER_HOUR = env_positive_int("TRIAL_IP_REQUESTS_PER_HOUR", 20)
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
if IS_RENDER and not SUPPORT_EMAIL:
    raise RuntimeError("Set SUPPORT_EMAIL in Render's environment before starting the service.")

usage_store = UsageStore(DATABASE_URL, require_external_database=IS_RENDER)

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
    payload = {"error": message}
    if session.get("auth_user"):
        try:
            payload["remaining_usage"] = remaining_usage()
        except Exception:
            pass
    return jsonify(payload), status


@app.before_request
def protect_routes_and_posts():
    public_endpoints = {
        "health", "login", "login_google", "auth0_callback", "privacy", "terms", "static",
    }
    auth_user = session.get("auth_user", {})
    if (
        auth_user
        and not TRIAL_SIGNUPS_ENABLED
        and auth_user.get("email", "").strip().lower() not in TRIAL_ALLOWED_EMAILS
    ):
        session.clear()
    if request.endpoint not in public_endpoints and not session.get("auth_user"):
        if request.path.startswith("/api/"):
            return api_error("Sign in to continue.", 401)
        return redirect(url_for("login"))

    if request.method == "POST":
        expected = session.get("csrf_token", "")
        supplied = request.headers.get("X-CSRF-Token", "")
        if not supplied and not request.path.startswith("/api/"):
            supplied = request.form.get("_csrf", "")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            if request.path.startswith("/api/"):
                return api_error("The request could not be verified. Refresh the page and try again.", 400)
            abort(400)

        if request.path in {
            "/api/analyze", "/api/job-match", "/api/cover-letter", "/api/tools",
        }:
            auth_user = session.get("auth_user", {})
            try:
                usage_store.reserve_rate_limits(
                    account_key=account_key(auth_user),
                    ip_key=client_ip_key(),
                    account_limit=TRIAL_ACCOUNT_REQUESTS_PER_HOUR,
                    ip_limit=TRIAL_IP_REQUESTS_PER_HOUR,
                    now=int(time.time()),
                )
            except TrialLimitExceeded as error:
                return api_error(str(error), 429)
            except Exception:
                app.logger.exception("Could not reserve a trial rate limit.")
                return api_error("The trial service is temporarily unavailable. Please try again shortly.", 503)


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
    auth_user = session.get("auth_user")
    return {
        "auth_user": auth_user,
        "account_usage": remaining_usage() if auth_user else {},
        "support_email": SUPPORT_EMAIL,
    }


def account_key(auth_user=None):
    auth_user = auth_user or session.get("auth_user", {})
    subject = str(auth_user.get("sub", "")).strip()
    if not subject:
        raise PermissionError("Sign in to use this feature.")
    return usage_store.account_key(subject)


def client_ip_key():
    # Render routes public traffic through Cloudflare and overwrites CF-Connecting-IP.
    forwarded_ip = request.headers.get("CF-Connecting-IP", "") if IS_RENDER else ""
    candidate = forwarded_ip.strip() or request.remote_addr or "unknown"
    try:
        normalized_ip = str(ipaddress.ip_address(candidate))
    except ValueError:
        normalized_ip = "unknown"
    return hmac.new(
        app.secret_key.encode("utf-8"), normalized_ip.encode("utf-8"), "sha256"
    ).hexdigest()


def reserve_feature_request(feature):
    try:
        usage_store.reserve_feature(
            account_key=account_key(),
            feature=feature,
            limit=USAGE_LIMITS[feature],
            now=int(time.time()),
        )
    except TrialLimitExceeded as error:
        raise PermissionError(str(error)) from error


def remaining_usage():
    auth_user = session.get("auth_user", {})
    if not auth_user.get("sub"):
        return dict(USAGE_LIMITS)
    return usage_store.remaining(account_key=account_key(auth_user), limits=USAGE_LIMITS)


def limited_form_text(field_name, label, max_chars, *, required=False):
    value = request.form.get(field_name, "")
    if len(value) > max_chars:
        raise ValueError(f"{label} must be {max_chars:,} characters or fewer.")
    if required and not value.strip():
        raise ValueError(f"{label} is required.")
    return value.strip()


def require_processing_consent():
    if request.form.get("processing_consent", "").lower() not in ("1", "true", "on", "yes"):
        raise ValueError("Confirm the data-processing notice before continuing.")


def get_resume_upload(field_name="resume"):
    uploaded = request.files.get(field_name)
    if uploaded is None or not uploaded.filename:
        raise ValueError("Choose a supported resume file to continue.")
    filename = secure_filename(uploaded.filename)
    allowed_extensions = (
        ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt",
        ".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".bmp", ".webp",
    )
    if not filename or os.path.splitext(filename)[1].lower() not in allowed_extensions:
        raise ValueError("Unsupported file format. Use a PDF, Word, OpenDocument, RTF, text, or image file.")
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
    deadline_token = set_request_deadline(105)
    try:
        return jsonify(operation())
    except ValueError as error:
        return api_error(str(error), 400)
    except PermissionError as error:
        return api_error(str(error), 429)
    except AffindaParserError as error:
        return api_error(str(error), error.status_code)
    except OpenAIConfigurationError as error:
        return api_error(str(error), 503)
    except RuntimeError as error:
        app.logger.warning("A provider request failed (%s).", type(error).__name__)
        return api_error("A service took too long or could not complete the request. Please try again.", 502)
    except Exception:
        # Avoid returning prompts, resume text, credentials, or internal traces to the browser.
        app.logger.exception("A resume analysis request failed.")
        return api_error("The analysis could not be completed. Check the service settings and try again.", 502)
    finally:
        reset_request_deadline(deadline_token)


@app.get("/health")
def health():
    try:
        usage_store.ping()
    except Exception:
        app.logger.exception("The trial usage database health check failed.")
        return jsonify({"status": "unavailable"}), 503
    return jsonify({"status": "ok"})


@app.get("/login")
def login():
    if session.get("auth_user"):
        return redirect(url_for("index"))
    return render_template(
        "login.html",
        csrf_token=ensure_csrf_token(),
        auth0_configured=AUTH0_CONFIGURED,
        invite_only=not TRIAL_SIGNUPS_ENABLED,
        trial_has_invites=bool(TRIAL_ALLOWED_EMAILS),
        errors=get_flashed_messages(with_categories=True),
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
        if not TRIAL_SIGNUPS_ENABLED and userinfo["email"].strip().lower() not in TRIAL_ALLOWED_EMAILS:
            session.clear()
            flash("This ResuMate trial is invite-only. Ask the trial organizer for access.", "error")
            return redirect(url_for("login"))
        session.clear()
        session["auth_user"] = {
            "sub": subject,
            "email": userinfo["email"],
            "name": userinfo.get("name") or userinfo["email"],
        }
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


@app.post("/account/delete-trial-data")
def delete_trial_data():
    user = session.get("auth_user", {})
    try:
        usage_store.delete_account(account_key=account_key(user))
    except Exception:
        app.logger.exception("Could not delete trial usage data for an account.")
        return api_error("Your trial data could not be deleted right now. Please contact support.", 503)
    session.clear()
    flash("Your saved resume history and ResuMate trial data have been deleted. Provider retention is managed separately.", "success")
    if not AUTH0_CONFIGURED:
        return redirect(url_for("login"))
    params = urlencode({"client_id": AUTH0_CLIENT_ID, "returnTo": AUTH0_LOGOUT_RETURN_URL})
    return redirect(f"https://{AUTH0_DOMAIN}/v2/logout?{params}")


@app.get("/privacy")
def privacy():
    return render_template("privacy.html", support_email=SUPPORT_EMAIL, csrf_token=ensure_csrf_token())


@app.get("/terms")
def terms():
    return render_template("terms.html", support_email=SUPPORT_EMAIL, csrf_token=ensure_csrf_token())


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
        job_role = limited_form_text("job_role", "Target role", MAX_CONTEXT_FIELD_CHARS)
        require_processing_consent()
        focus_areas = request.form.getlist("focus_areas")
        focus_areas = [item for item in focus_areas if item in FOCUS_AREAS]
        reserve_feature_request("resume_analysis")
        result = analyze_resume(
            filename,
            file_bytes,
            analysis_mode=request.form.get("analysis_mode", "Standard Analysis"),
            focus_areas=focus_areas,
            job_role=job_role,
            enable_statistics=parse_bool("enable_statistics", True),
            enable_readability=parse_bool("enable_readability", True),
            enable_action_verbs=parse_bool("enable_action_verbs", False),
        )
        history_payload = {
            key: value
            for key, value in result.items()
            if key not in {"extracted_text_preview", "text_preview_truncated"}
        }
        try:
            result["history_entry"] = usage_store.save_resume_history(
                account_key=account_key(),
                payload=history_payload,
                created_at=int(time.time()),
            )
            result["history_saved"] = True
        except Exception:
            # Return the completed review even if persistence is temporarily unavailable.
            app.logger.exception("Could not save a completed resume review to account history.")
            result["history_saved"] = False
        result["remaining_usage"] = remaining_usage()
        return result
    return run_api_operation(operation)


@app.get("/api/history")
def api_history():
    try:
        entries = usage_store.list_resume_history(account_key=account_key())
    except Exception:
        app.logger.exception("Could not load saved resume history.")
        return api_error("Saved history could not be loaded right now. Please try again.", 503)
    return jsonify({"entries": entries})


@app.post("/api/history/clear")
def api_clear_history():
    try:
        usage_store.clear_resume_history(account_key=account_key())
    except Exception:
        app.logger.exception("Could not clear saved resume history.")
        return api_error("Saved history could not be cleared right now. Please try again.", 503)
    return jsonify({"ok": True})


@app.post("/api/job-match")
def api_job_match():
    def operation():
        filename, file_bytes = get_resume_upload()
        job_description = limited_form_text(
            "job_description", "Job description", MAX_JOB_DESCRIPTION_CHARS, required=True
        )
        job_title = limited_form_text("job_title", "Job title", MAX_CONTEXT_FIELD_CHARS)
        require_processing_consent()
        reserve_feature_request("job_match")
        result = analyze_job_match(
            filename,
            file_bytes,
            job_description,
            job_title=job_title,
        )
        result["remaining_usage"] = remaining_usage()
        return result
    return run_api_operation(operation)


@app.post("/api/cover-letter")
def api_cover_letter():
    def operation():
        filename, file_bytes = get_resume_upload()
        job_description = limited_form_text(
            "job_description", "Job description", MAX_JOB_DESCRIPTION_CHARS, required=True
        )
        company = limited_form_text("company", "Company name", MAX_CONTEXT_FIELD_CHARS)
        role = limited_form_text("role", "Job title", MAX_CONTEXT_FIELD_CHARS)
        require_processing_consent()
        tone = request.form.get("tone", "Professional")
        allowed_tones = ("Professional", "Enthusiastic", "Formal", "Creative", "Conversational")
        if tone not in allowed_tones:
            tone = "Professional"
        reserve_feature_request("cover_letter")
        letter = generate_cover_letter(
            filename,
            file_bytes,
            job_description,
            company=company,
            role=role,
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
        text = limited_form_text("tool_text", "Resume text", MAX_TOOL_TEXT_CHARS)
        if tool_name not in TOOLS:
            raise ValueError("Choose a valid resume tool.")
        if tool_name == "Interview Question Generator":
            file_name, file_bytes = get_resume_upload("interview_resume")
        elif not text.strip():
            raise ValueError("Enter resume content before running this tool.")
        require_processing_consent()
        target_industry = limited_form_text("target_industry", "Target industry", MAX_CONTEXT_FIELD_CHARS)
        target_role = limited_form_text("target_role", "Target role", MAX_CONTEXT_FIELD_CHARS)
        reserve_feature_request("resume_tools")
        output = generate_tool_output(
            tool_name,
            text,
            file_name=file_name,
            file_bytes=file_bytes,
            target_industry=target_industry,
            target_role=target_role,
        )
        return {"output": output, "remaining_usage": remaining_usage()}
    return run_api_operation(operation)


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    return api_error("The request exceeds the 22 MB upload limit.", 413)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
