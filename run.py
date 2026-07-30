import json
import importlib
import os
from pathlib import Path
from flask import Flask, Blueprint, jsonify
from dotenv import load_dotenv

# Load .env from project root (if present)
load_dotenv()


def create_app():

    app = Flask(__name__)

    # Basic configuration
    app.config.setdefault('SECRET_KEY', os.environ.get('SECRET_KEY', 'dev-secret'))
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', os.environ.get('DATABASE_URL', 'sqlite:///main.db'))
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

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

    # default minimal route (fallback)
    bp = Blueprint('main', __name__)

    app.register_blueprint(bp)

    # initialize extensions
    from extensions import db, login_manager

    db.init_app(app)
    login_manager.init_app(app)
    # where to redirect for login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bitte melde dich an, um diese Seite zu sehen.'

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
            mod_name = f"{pkg}.app"
            try:
                mod = importlib.import_module(mod_name)
            except Exception as e:
                print(f"Failed importing module '{mod_name}': {e}")
                continue

            # If the auth module was just loaded, set up the user loader
            if pkg.endswith('auth'):
                try:
                    from models import User

                    from extensions import login_manager

                    @login_manager.user_loader
                    def load_user(user_id):
                        return User.query.get(int(user_id))
                except Exception:
                    pass

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

    return app


app = create_app()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run the Flask app')
    parser.add_argument('--debug', action='store_true', help='Run server in debug mode')
    args = parser.parse_args()

    if args.debug:
        host = '127.0.0.1'
        debug_mode = True
    else:
        host = '0.0.0.0'
        debug_mode = False

    app.run(host=host, port=5000, debug=debug_mode)
