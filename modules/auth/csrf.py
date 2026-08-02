"""Small session-backed CSRF protection for browser forms."""

import hmac
import secrets
from functools import wraps

from flask import abort, request, session


_SESSION_KEY = '_csrf_token'


def csrf_token() -> str:
    """Return the current signed-session CSRF token, creating it if needed."""
    token = session.get(_SESSION_KEY)
    if not isinstance(token, str) or len(token) < 32:
        token = secrets.token_urlsafe(32)
        session[_SESSION_KEY] = token
    return token


def csrf_protect(view):
    """Reject state-changing browser requests without a valid session token."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.method == 'POST' and not validate_csrf(request.form.get('csrf_token')):
            abort(400)
        return view(*args, **kwargs)

    return wrapped


def rotate_csrf() -> str:
    """Rotate the token after an authentication boundary."""
    session.pop(_SESSION_KEY, None)
    return csrf_token()


def validate_csrf(token: str | None) -> bool:
    """Constant-time validation of a submitted form token."""
    expected = session.get(_SESSION_KEY)
    return (
        isinstance(token, str)
        and isinstance(expected, str)
        and hmac.compare_digest(token, expected)
    )
