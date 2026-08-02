import re
import threading
from datetime import datetime
import time
from urllib.parse import urlparse

from authlib.integrations.base_client.errors import MismatchingStateError, OAuthError
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from requests import RequestException
from sqlalchemy import or_, update
from sqlalchemy.exc import SQLAlchemyError
from flask_login import current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import User, LoginSession, ServerKey, RegistrationSettings
from modules.auth import oauth
from modules.auth.csrf import csrf_protect, rotate_csrf

bp = Blueprint('auth', __name__, url_prefix='/auth')

# --- Validation constants ---
USERNAME_RE = re.compile(r'^[A-Za-z0-9._-]{3,32}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MAX_PASSWORD_LEN = 128
MAX_EMAIL_LEN = 200
REGISTRATION_KEY_SESSION = 'registration_key_id'
PENDING_GITHUB_SESSION = 'pending_github'

# Dummy hash so unknown usernames take the same time as known ones
_DUMMY_HASH = generate_password_hash('mjl-dummy-password-for-timing')

# --- Simple in-memory rate limiter (per IP + action) ---
_attempts = {}
_attempts_lock = threading.Lock()
RATE_LIMIT = 5          # attempts
RATE_WINDOW = 60        # seconds


def _rate_limited(key: str) -> bool:
    """Return True if the request should be blocked (too many attempts)."""
    now = time.time()
    with _attempts_lock:
        stamps = [t for t in _attempts.get(key, []) if now - t < RATE_WINDOW]
        if len(stamps) >= RATE_LIMIT:
            _attempts[key] = stamps
            return True
        stamps.append(now)
        _attempts[key] = stamps
        return False


def _client_key(action: str) -> str:
    return f"{action}:{request.remote_addr or 'local'}"


def _is_safe_next(url: str | None) -> bool:
    """Only allow relative, same-site redirect targets (prevents open redirects)."""
    if not url:
        return False
    # Normalize backslashes (browsers treat \\ like /), then reject anything
    # that is not a plain same-site path: //evil.com, \\evil.com, /\\evil.com, https://...
    url = url.strip().replace('\\', '/')
    if not url.startswith('/') or url.startswith('//'):
        return False
    parsed = urlparse(url)
    return not parsed.scheme and not parsed.netloc


def _github_response_json(response):
    """Validate a GitHub response and return its JSON payload."""
    response.raise_for_status()
    payload = response.json()
    if not payload:
        raise ValueError('GitHub returned an empty response')
    return payload


def _extract_github_email(emails):
    """Return only GitHub's primary, verified email address."""
    if not isinstance(emails, list):
        return None
    primary = next(
        (item.get('email') for item in emails
         if isinstance(item, dict) and item.get('primary') and item.get('verified') and item.get('email')),
        None,
    )
    return primary


def _authenticate(username: str, password: str):
    """Look up the user and verify the password, equalizing timing for unknown users."""
    user = User.query.filter((User.username == username) | (User.email == username)).first()
    if user is None:
        # Keep timing constant for unknown usernames
        check_password_hash(_DUMMY_HASH, password)
        return None
    if user.check_password(password):
        return user
    return None


def _parse_user_agent(ua: str):
    """Simple user-agent parser – extracts browser, OS, device type."""
    ua_lower = ua.lower()

    # Browser
    browser = 'Unknown'
    browser_version = ''
    if 'edg/' in ua_lower:
        browser = 'Edge'
        m = re.search(r'edg/([\d.]+)', ua_lower)
        if m: browser_version = m.group(1)
    elif 'chrome/' in ua_lower and 'chromium' not in ua_lower:
        browser = 'Chrome'
        m = re.search(r'chrome/([\d.]+)', ua_lower)
        if m: browser_version = m.group(1)
    elif 'firefox/' in ua_lower:
        browser = 'Firefox'
        m = re.search(r'firefox/([\d.]+)', ua_lower)
        if m: browser_version = m.group(1)
    elif 'safari/' in ua_lower:
        browser = 'Safari'
        m = re.search(r'version/([\d.]+)', ua_lower)
        if m: browser_version = m.group(1)

    # OS
    os_name = 'Unknown'
    os_version = ''
    if 'windows nt 10' in ua_lower:
        os_name = 'Windows'; os_version = '10/11'
    elif 'windows nt 6.3' in ua_lower:
        os_name = 'Windows'; os_version = '8.1'
    elif 'windows nt 6.1' in ua_lower:
        os_name = 'Windows'; os_version = '7'
    elif 'mac os x' in ua_lower:
        os_name = 'macOS'
        m = re.search(r'mac os x ([\d_]+)', ua_lower)
        if m: os_version = m.group(1).replace('_', '.')
    elif 'linux' in ua_lower and 'android' not in ua_lower:
        os_name = 'Linux'
    elif 'android' in ua_lower:
        os_name = 'Android'
        m = re.search(r'android ([\d.]+)', ua_lower)
        if m: os_version = m.group(1)
    elif 'iphone' in ua_lower or 'ipad' in ua_lower:
        os_name = 'iOS'
        m = re.search(r'os ([\d_]+)', ua_lower)
        if m: os_version = m.group(1).replace('_', '.')

    # Device type
    device_type = 'Desktop'
    if 'mobile' in ua_lower or 'android' in ua_lower:
        device_type = 'Mobile'
    elif 'ipad' in ua_lower or 'tablet' in ua_lower:
        device_type = 'Tablet'

    return browser, browser_version, os_name, os_version, device_type


def _track_login(user: User):
    """Create a LoginSession record with browser/device data from the client form."""
    ua = request.headers.get('User-Agent', '')
    browser, browser_version, os_name, os_version, device_type = _parse_user_agent(ua)

    login_session = LoginSession(
        user_id=user.id,
        ip_address=request.remote_addr or 'unknown',
        user_agent=ua[:500] if ua else None,
        browser=browser,
        browser_version=browser_version,
        os=os_name,
        os_version=os_version,
        device_type=device_type,
        screen_width=request.form.get('screen_w', type=int),
        screen_height=request.form.get('screen_h', type=int),
        language=(request.form.get('lang') or '')[:10] or None,
    )
    db.session.add(login_session)
    db.session.commit()

    # Keep only the 2 latest sessions per user
    old_sessions = LoginSession.query.filter_by(user_id=user.id)\
        .order_by(LoginSession.logged_in_at.desc())\
        .offset(2).all()
    for old in old_sessions:
        db.session.delete(old)
    db.session.commit()


def _registration_settings() -> RegistrationSettings:
    """Return the singleton registration policy row."""
    settings = db.session.get(RegistrationSettings, 1)
    if settings is None:
        settings = RegistrationSettings(id=1, server_keys_required=True)
        db.session.add(settings)
        db.session.commit()
    return settings


def _server_keys_required() -> bool:
    return bool(_registration_settings().server_keys_required)


def _clear_registration_key() -> None:
    session.pop(REGISTRATION_KEY_SESSION, None)


def _pending_github() -> dict | None:
    payload = session.get(PENDING_GITHUB_SESSION)
    return payload if isinstance(payload, dict) else None


def _clear_pending_github() -> None:
    session.pop(PENDING_GITHUB_SESSION, None)


def _verified_registration_key():
    key_id = session.get(REGISTRATION_KEY_SESSION)
    if not key_id:
        return None
    key = db.session.get(ServerKey, key_id)
    if key is None or not key.is_currently_active or key.uses_left <= 0:
        _clear_registration_key()
        return None
    return key


def _handle_login(template: str):
    """Shared login POST handling used by both login routes."""
    if request.method != 'POST':
        return None

    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    user = _authenticate(username, password)

    if user:
        if user.banned:
            flash('Dieser Account wurde gesperrt.', 'error')
            return None
        # Successful login resets the attempt counter for this client
        with _attempts_lock:
            _attempts.pop(_client_key('login'), None)
        _track_login(user)
        session.clear()
        login_user(user, remember=bool(request.form.get('remember')))
        session['user_id'] = user.id
        rotate_csrf()
        next_url = request.args.get('next') or request.form.get('next')
        if _is_safe_next(next_url):
            return redirect(next_url)
        return redirect(url_for('hub.hub'))

    # Only failed attempts count towards the rate limit. This way a user who
    # mistyped 5 times can still get in with the correct password.
    if _rate_limited(_client_key('login')):
        flash('Zu viele Versuche. Bitte warte kurz und versuche es erneut.', 'error')
        return render_template(template), 429

    flash('Ungültiger Benutzername oder Passwort', 'error')
    return None


@bp.route('/login/github')
def github_login():
    """Start GitHub OAuth only after the registration gate is satisfied."""
    if current_user.is_authenticated:
        return redirect(url_for('hub.dashboard'))
    if _server_keys_required() and _verified_registration_key() is None:
        # Continue the OAuth request only after the registration gate; the
        # gate page itself never exposes a GitHub button.
        session['oauth_after_key'] = True
        flash('Bitte zuerst den Server-Key bestätigen.', 'info')
        return redirect(url_for('auth.register'))
    if not current_app.config.get('GITHUB_CLIENT_ID') or not current_app.config.get('GITHUB_CLIENT_SECRET'):
        flash('GitHub-Anmeldung ist derzeit nicht konfiguriert.', 'error')
        return redirect(url_for('auth.login'))

    redirect_uri = current_app.config['GITHUB_REDIRECT_URI']
    current_app.logger.info('GitHub OAuth redirect_uri=%s', redirect_uri)
    return oauth.github.authorize_redirect(redirect_uri)


@bp.route('/github/callback')
def github_callback():
    """Finish GitHub OAuth, create/link the local user and start the session."""
    if request.args.get('error'):
        flash('GitHub-Anmeldung abgebrochen. Bitte versuche es erneut.', 'error')
        return redirect(url_for('auth.login'))

    try:
        token = oauth.github.authorize_access_token()
        if not token or not token.get('access_token'):
            raise ValueError('GitHub did not return an access token')

        github_user = _github_response_json(oauth.github.get('user'))
        github_emails = _github_response_json(oauth.github.get('user/emails'))
        if not isinstance(github_user, dict) or not isinstance(github_emails, list):
            raise ValueError('GitHub returned an invalid profile response')
        github_id = str(github_user.get('id') or '')
        email = (_extract_github_email(github_emails) or '').strip().lower()
        if not github_id or not email or len(email) > MAX_EMAIL_LEN or not EMAIL_RE.fullmatch(email):
            raise ValueError('GitHub profile has no usable primary email')

        # The server-key gate must still be valid when GitHub redirects back;
        # an admin may have paused or exhausted the key during OAuth.
        if _server_keys_required() and _verified_registration_key() is None:
            # Keep the continuation marker so re-verifying a replacement key
            # starts OAuth again without exposing GitHub on the gate page.
            session['oauth_after_key'] = True
            flash('Der Server-Key ist nicht mehr gültig. Bitte bestätige ihn erneut.', 'error')
            return redirect(url_for('auth.register'))
    except (MismatchingStateError, OAuthError, RequestException, SQLAlchemyError, ValueError, TypeError):
        flash('GitHub-Anmeldung konnte nicht abgeschlossen werden. Bitte versuche es erneut.', 'error')
        return redirect(url_for('auth.login'))

    try:
        user = User.query.filter_by(github_id=github_id).first()
        existing_email_user = User.query.filter_by(email=email).first()
    except SQLAlchemyError:
        db.session.rollback()
        flash('GitHub-Anmeldung konnte nicht abgeschlossen werden. Bitte versuche es erneut.', 'error')
        return redirect(url_for('auth.login'))

    if existing_email_user and (user is None or existing_email_user.id != user.id):
        # Do not silently take over or overwrite another local account solely
        # because the same email appears in GitHub. Explicit linking can be
        # added later after the user has authenticated locally.
        flash('Für diese E-Mail existiert bereits ein lokales Konto. Bitte zuerst lokal anmelden.', 'error')
        return redirect(url_for('auth.login'))

    if user is None:
        # GitHub never creates an account silently. Keep only the verified
        # profile data in the signed session so the user can explicitly finish
        # the normal password-based signup; the registration page has no OAuth
        # button and the password remains mandatory.
        session[PENDING_GITHUB_SESSION] = {
            'github_id': github_id,
            'email': email,
            'login': (github_user.get('login') or '')[:32],
            'avatar_url': (github_user.get('avatar_url') or '')[:500],
        }
        flash('Für diesen GitHub-Account existiert noch kein Konto. Bitte erstelle zuerst ein Konto mit Passwort.', 'info')
        return redirect(url_for('auth.register'))
    else:
        user.github_id = github_id
        if not user.email:
            user.email = email
        user.avatar_url = (github_user.get('avatar_url') or '')[:500] or user.avatar_url

    if user.banned:
        db.session.rollback()
        flash('Dieser Account wurde gesperrt.', 'error')
        return redirect(url_for('auth.login'))

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('GitHub-Anmeldung konnte nicht abgeschlossen werden. Bitte versuche es erneut.', 'error')
        return redirect(url_for('auth.login'))

    try:
        _track_login(user)
    except Exception:
        db.session.rollback()
        flash('GitHub-Anmeldung konnte nicht abgeschlossen werden. Bitte versuche es erneut.', 'error')
        return redirect(url_for('auth.login'))

    session.clear()
    login_user(user)
    session['user_id'] = user.id
    rotate_csrf()
    return redirect(url_for('hub.dashboard'))


@bp.route('/login', methods=['GET', 'POST'])
@csrf_protect
def login():
    # redirect authenticated users to hub
    if current_user.is_authenticated:
        return redirect(url_for('hub.hub'))
    result = _handle_login('auth/login.html')
    if result is not None:
        return result
    next_url = request.args.get('next')
    return render_template('auth/login.html', next=next_url if _is_safe_next(next_url) else None)


@bp.route('/login-split', methods=['GET', 'POST'])
@csrf_protect
def login_split():
    if current_user.is_authenticated:
        return redirect(url_for('hub.hub'))
    result = _handle_login('auth/login-split.html')
    if result is not None:
        return result
    next_url = request.args.get('next')
    return render_template('auth/login-split.html', next=next_url if _is_safe_next(next_url) else None)


@bp.route('/register', methods=['GET', 'POST'])
@csrf_protect
def register():
    """Show the server-key gate, then create a local account."""
    action = request.form.get('action', '') if request.method == 'POST' else ''
    rate_key = 'register-key' if action == 'verify_key' else 'register'
    if request.method == 'POST' and _rate_limited(_client_key(rate_key)):
        flash('Zu viele Versuche. Bitte warte kurz und versuche es erneut.', 'error')
        return render_template('auth/register.html',
                               key_required=_server_keys_required(),
                               key_verified=bool(_verified_registration_key()),
                               ), 429

    if current_user.is_authenticated:
        return redirect(url_for('hub.hub'))

    if request.method == 'POST' and request.form.get('action') == 'clear_key':
        _clear_registration_key()
        return redirect(url_for('auth.register'))

    if request.method == 'POST' and request.form.get('action') == 'verify_key':
        submitted_key = (request.form.get('server_key') or '').strip()
        key = ServerKey.query.filter_by(key_value=submitted_key).first() if submitted_key else None
        if not _server_keys_required():
            return redirect(url_for('auth.register'))
        if key is None or not key.is_currently_active or key.uses_left <= 0:
            flash('Server-Key ist ungültig, deaktiviert oder bereits aufgebraucht.', 'error')
            return render_template('auth/register.html', key_required=True, key_verified=False,
                                   )
        session[REGISTRATION_KEY_SESSION] = key.id
        if session.pop('oauth_after_key', False):
            return redirect(url_for('auth.github_login'))
        flash('Server-Key bestätigt. Du kannst jetzt dein Konto erstellen.', 'success')
        return redirect(url_for('auth.register'))

    key_required = _server_keys_required()
    verified_key = _verified_registration_key() if key_required else True
    pending_github = _pending_github()
    if request.method == 'POST':
        if key_required and verified_key is None:
            flash('Bitte zuerst einen gültigen Server-Key bestätigen.', 'error')
            return render_template('auth/register.html', key_required=True, key_verified=False,
                                   )

        username = (request.form.get('username') or '').strip()
        email = (pending_github or {}).get('email') or (request.form.get('email') or '').strip().lower() or None
        password = request.form.get('password') or ''
        if not username or not password:
            flash('Benutzername und Passwort sind erforderlich', 'error')
            return render_template('auth/register.html', key_required=key_required,
                                   key_verified=bool(verified_key), pending_github=pending_github)
        if not USERNAME_RE.match(username):
            flash('Benutzername: 3–32 Zeichen, nur Buchstaben, Zahlen, Punkt, Minus und Unterstrich', 'error')
            return render_template('auth/register.html', key_required=key_required,
                                   key_verified=bool(verified_key), pending_github=pending_github)
        if len(password) > MAX_PASSWORD_LEN:
            flash('Passwort darf höchstens 128 Zeichen haben', 'error')
            return render_template('auth/register.html', key_required=key_required,
                                   key_verified=bool(verified_key), pending_github=pending_github)
        if email and (len(email) > MAX_EMAIL_LEN or not EMAIL_RE.fullmatch(email)):
            flash('Bitte eine gültige E-Mail-Adresse angeben', 'error')
            return render_template('auth/register.html', key_required=key_required,
                                   key_verified=bool(verified_key), pending_github=pending_github)
        valid, reasons = validate_password(password, username)
        if not valid:
            flash('Passwort entspricht nicht der Sicherheitsrichtlinie: ' + '; '.join(reasons), 'error')
            return render_template('auth/register.html', key_required=key_required,
                                   key_verified=bool(verified_key), pending_github=pending_github)
        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben', 'error')
            return render_template('auth/register.html', key_required=key_required,
                                   key_verified=bool(verified_key), pending_github=pending_github)
        if email and User.query.filter_by(email=email).first():
            flash('E-Mail bereits registriert', 'error')
            return render_template('auth/register.html', key_required=key_required,
                                   key_verified=bool(verified_key), pending_github=pending_github)

        user = User(username=username, email=email, role=1)
        if pending_github:
            user.github_id = pending_github['github_id']
            user.avatar_url = pending_github.get('avatar_url') or None
        user.set_password(password)
        db.session.add(user)
        if key_required:
            # Re-check immediately before consuming so deactivated/exhausted
            # keys cannot be used after the gate page was opened.
            if verified_key is None:
                db.session.rollback()
                _clear_registration_key()
                flash('Der Server-Key ist nicht mehr gültig.', 'error')
                return render_template('auth/register.html', key_required=True, key_verified=False,
                                       )
            result = db.session.execute(
                update(ServerKey)
                .where(
                    ServerKey.id == verified_key.id,
                    ServerKey.active.is_(True),
                    or_(
                        ServerKey.deactivated_until.is_(None),
                        ServerKey.deactivated_until <= datetime.utcnow(),
                    ),
                    ServerKey.uses_left > 0,
                )
                .values(uses_left=ServerKey.uses_left - 1)
            )
            if result.rowcount != 1:
                db.session.rollback()
                _clear_registration_key()
                flash('Der Server-Key ist nicht mehr gültig.', 'error')
                return render_template('auth/register.html', key_required=True, key_verified=False,
                                       )
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Konto konnte nicht erstellt werden. Bitte versuche es erneut.', 'error')
            return render_template('auth/register.html', key_required=key_required,
                                   key_verified=bool(verified_key), pending_github=pending_github)
        _clear_registration_key()
        _clear_pending_github()
        session.clear()
        login_user(user)
        session['user_id'] = user.id
        rotate_csrf()
        return redirect(url_for('hub.hub'))

    return render_template('auth/register.html', key_required=key_required,
                           key_verified=bool(verified_key), pending_github=pending_github)


@bp.route('/logout', methods=['GET', 'POST'])
@csrf_protect
def logout():
    # Keep legacy GET links usable without making logout CSRF-able. Actual
    # session destruction happens only after the CSRF-protected POST.
    if request.method == 'GET':
        return render_template('auth/logout_confirm.html')
    logout_user()
    session.clear()
    # The root route is login-protected, so the public start page is the login screen.
    return redirect(url_for('auth.login'))


def init_module(app):
    app.register_blueprint(bp)


def validate_password(password: str, username: str | None = None):


    reasons = []
    if not password or len(password) < 8:
        reasons.append('mindestens 8 Zeichen')
    if not re.search(r'[A-Za-z]', password):
        reasons.append('mindestens ein Buchstabe')
    if not re.search(r'[0-9]', password):
        reasons.append('mindestens eine Zahl')
    return (len(reasons) == 0, reasons)
