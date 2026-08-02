from functools import wraps

from flask import current_app, redirect, session, url_for
from flask_login import current_user, login_user, logout_user

from extensions import db
from models import User


def login_required(view):
    """Require the app session user and redirect unauthenticated visitors."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id and current_user.is_authenticated:
            user_id = current_user.id
            session['user_id'] = user_id

        try:
            user_id = int(user_id) if user_id is not None else None
        except (TypeError, ValueError):
            user_id = None

        user = db.session.get(User, user_id) if user_id else None
        if user is None or user.banned:
            logout_user()
            session.pop('user_id', None)
            endpoint = (
                'auth.github_login'
                if current_app.config.get('GITHUB_CLIENT_ID')
                and current_app.config.get('GITHUB_CLIENT_SECRET')
                else 'auth.login'
            )
            return redirect(url_for(endpoint))

        if not current_user.is_authenticated or current_user.id != user.id:
            login_user(user)
        return view(*args, **kwargs)

    return wrapped
