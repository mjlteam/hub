import json
import importlib
from pathlib import Path
from flask import Flask, Blueprint, jsonify, redirect


def create_app():
    """Create and configure the Flask application.

    Loads modules defined in `modules.json` at the project root. Each module
    should expose either a `bp` Blueprint or an `init_module(app)` function
    in its `app.py`.
    """
    app = Flask(__name__)

    # default minimal route (fallback)
    bp = Blueprint('main', __name__)

    app.register_blueprint(bp)

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
