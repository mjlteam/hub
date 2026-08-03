import json
import importlib
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from flask import Flask, flash, redirect, render_template, session, url_for
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db, login_manager
from models import User
from modules.auth.csrf import csrf_token
from schema import ensure_database_schema
from flask_login import current_user, logout_user
from datetime import datetime

# Load .env from project root (if present)
load_dotenv()


# Cache the git commit short id — do not spawn a subprocess on every request
_commit_cache = None


def _configured_github_redirect_uri() -> str | None:
    """Return an explicit GitHub callback URI, or None for request-based discovery.

    GitHub compares this URI exactly. Leaving it unset lets the login request
    determine the public host/scheme, which avoids a localhost/127.0.0.1
    mismatch during local development and works with a configured proxy.
    """
    value = os.environ.get('GITHUB_REDIRECT_URI', '').strip()
    if not value:
        return None

    parsed = urlparse(value)
    if (
        parsed.scheme not in {'http', 'https'}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.path != '/auth/github/callback'
        or value.endswith('/')
    ):
        raise RuntimeError(
            'GITHUB_REDIRECT_URI must be an http(s) URL ending exactly '
            'in /auth/github/callback without query, fragment, or trailing slash.'
        )
    return value


def _configure_proxy(app: Flask) -> None:
    """Honor forwarded public URL headers only when explicitly trusted."""
    trusted = os.environ.get('TRUST_PROXY', '').strip().lower() in {
        '1', 'true', 'yes', 'on',
    }
    if trusted:
        # Trust only the headers needed to build the public OAuth URL. The
        # deployment must not expose the app directly when this is enabled.
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_proto=1,
            x_host=1,
            x_port=1,
            x_prefix=1,
        )


def get_git_commit(project_root: Path) -> str | None:
    """Return the short git commit id of project_root, computed once and cached."""
    global _commit_cache
    if _commit_cache is None:
        try:
            _commit_cache = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=project_root,
                stderr=subprocess.DEVNULL,
            ).decode().strip()
        except Exception:
            _commit_cache = ''
    return _commit_cache or None


def create_app():

    app = Flask(__name__)
    _configure_proxy(app)

    # Basic configuration (loaded from .env by python-dotenv above)
    app.config.setdefault('SECRET_KEY', os.environ.get('SECRET_KEY', 'dev-secret'))
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', os.environ.get('DATABASE_URL', 'sqlite:///main.db'))
    app.config['GITHUB_CLIENT_ID'] = os.environ.get('GITHUB_CLIENT_ID', '')
    app.config['GITHUB_CLIENT_SECRET'] = os.environ.get('GITHUB_CLIENT_SECRET', '')
    # An explicit value is useful for a fixed production domain. If it is
    # absent, the OAuth route derives the callback from the current public URL.
    app.config['GITHUB_REDIRECT_URI'] = _configured_github_redirect_uri()
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    # Immer frische Templates laden (kein altes „Stark"/Haken mehr nach Edits)
    app.config.setdefault('TEMPLATES_AUTO_RELOAD', True)

    # Session / cookie hardening
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config.setdefault('REMEMBER_COOKIE_HTTPONLY', True)
    app.config.setdefault('REMEMBER_COOKIE_SAMESITE', 'Lax')
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get(
        'SESSION_COOKIE_SECURE', 'false'
    ).lower() == 'true'

    import secrets

    sk = app.config.get('SECRET_KEY')
    if not sk or sk == 'dev-secret':
        gen = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
        app.config['SECRET_KEY'] = gen
        app.secret_key = gen
        if sk == 'dev-secret':
            # warn about insecure default when used
            print('Warning: using generated SECRET_KEY or default dev-secret. Set SECRET_KEY in .env for persistence.')
    else:
        app.secret_key = sk

    # initialize extensions

    db.init_app(app)
    login_manager.init_app(app)
    # where to redirect for login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = None

    # Authlib is initialized by the auth module, but the OAuth client is bound
    # during app creation so its CSRF state lives in this app's session.
    auth_package = importlib.import_module('modules.auth')
    auth_package.init_oauth(app)

    # project root
    project_root = Path(__file__).resolve().parent
    modules_file = project_root / 'modules.json'

    if modules_file.exists():
        try:
            cfg = json.loads(modules_file.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Failed to read modules.json: {e}")
            return app

        for entry in cfg.get('modules', []):
            if not entry.get('enabled', True):
                continue
            pkg = entry.get('package') or entry.get('name')
            if not pkg:
                continue
            mod_name = pkg if pkg.endswith('.app') else f'{pkg}.app'
            if not mod_name.startswith('modules.'):
                mod_name = f'modules.{mod_name}'
            try:
                mod = importlib.import_module(mod_name)
            except Exception as e:
                print(f"Failed importing module '{mod_name}': {e}")
                continue

            # If the auth module was just loaded, set up the user loader
            if mod_name.endswith('.auth.app'):
                @login_manager.user_loader
                def load_user(user_id):
                    try:
                        return db.session.get(User, int(user_id))
                    except (TypeError, ValueError):
                        return None

            if hasattr(mod, 'bp'):
                try:
                    app.register_blueprint(mod.bp)
                except Exception as e:
                    print(f"Failed registering blueprint from {mod_name}: {e}")
            elif hasattr(mod, 'init_module'):
                try:
                    mod.init_module(app)
                except Exception as e:
                    print(f"Failed initializing module {mod_name}: {e}")

    ensure_database_schema(app)

    # provide helper functions to templates
    @app.context_processor
    def inject_now():
        # include current UTC datetime factory and git commit short id if available
        return {"now": datetime.utcnow, "version": get_git_commit(project_root), "csrf_token": csrf_token}


    # Log out banned users on their next request — the ban must take effect
    # immediately, not only on the next login attempt.
    @app.before_request
    def enforce_bans():
        if current_user.is_authenticated and current_user.banned:
            logout_user()
            session.clear()
            flash('Dieser Account wurde gesperrt.', 'error')
            return redirect(url_for('auth.login'))

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.exception(e)
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html'), 400

    return app


app = create_app()


def run_init_db(project_root: Path) -> None:
    init_db_script = project_root / 'scripts' / 'init_db.py'
    subprocess.run([sys.executable, str(init_db_script)], cwd=project_root, check=True)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run the Flask app')
    parser.add_argument('--debug', action='store_true', help='Run server in debug mode')
    args = parser.parse_args()

    if args.debug:
        # The callback is derived from the host used to open the app unless an
        # explicit GITHUB_REDIRECT_URI is configured.
        host = os.environ.get('FLASK_HOST', 'localhost')
        debug_mode = True
    else:
        host = '0.0.0.0'
        debug_mode = False

    run_init_db(Path(__file__).resolve().parent)
    app.run(host=host, port=5000, debug=debug_mode)
