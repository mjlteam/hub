import re
import threading
import time
from urllib.parse import urlparse

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import User

bp = Blueprint('auth', __name__, url_prefix='/auth')

# --- Validation constants ---
USERNAME_RE = re.compile(r'^[A-Za-z0-9._-]{3,32}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MAX_PASSWORD_LEN = 128
MAX_EMAIL_LEN = 200

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


def _handle_login(template: str):
    """Shared login POST handling used by both login routes."""
    if request.method != 'POST':
        return None

    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    user = _authenticate(username, password)

    if user:
        # Successful login resets the attempt counter for this client
        with _attempts_lock:
            _attempts.pop(_client_key('login'), None)
        login_user(user)
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


@bp.route('/login', methods=['GET', 'POST'])
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
def login_split():
    if current_user.is_authenticated:
        return redirect(url_for('hub.hub'))
    result = _handle_login('auth/login-split.html')
    if result is not None:
        return result
    next_url = request.args.get('next')
    return render_template('auth/login-split.html', next=next_url if _is_safe_next(next_url) else None)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    # Rate limit BEFORE the authenticated-redirect so bulk registrations
    if request.method == 'POST' and _rate_limited(_client_key('register')):
        flash('Zu viele Registrierungsversuche. Bitte warte kurz.', 'error')
        return render_template('auth/register.html'), 429

    # redirect authenticated users to hub
    if current_user.is_authenticated:
        return redirect(url_for('hub.hub'))
    if request.method == 'POST':

        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip() or None
        password = request.form.get('password') or ''

        if not username or not password:
            flash('Benutzername und Passwort sind erforderlich', 'error')
            return render_template('auth/register.html')

        if not USERNAME_RE.match(username):
            flash('Benutzername: 3–32 Zeichen, nur Buchstaben, Zahlen, Punkt, Minus und Unterstrich', 'error')
            return render_template('auth/register.html')

        if len(password) > MAX_PASSWORD_LEN:
            flash('Passwort darf höchstens 128 Zeichen haben', 'error')
            return render_template('auth/register.html')

        if email:
            if len(email) > MAX_EMAIL_LEN or not EMAIL_RE.match(email):
                flash('Bitte eine gültige E-Mail-Adresse angeben', 'error')
                return render_template('auth/register.html')

        # Password policy check
        valid, reasons = validate_password(password, username)
        if not valid:
            flash('Passwort entspricht nicht der Sicherheitsrichtlinie: ' + '; '.join(reasons), 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben', 'error')
            return render_template('auth/register.html')

        if email and User.query.filter_by(email=email).first():
            flash('E-Mail bereits registriert', 'error')
            return render_template('auth/register.html')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('hub.hub'))
    return render_template('auth/register.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
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
