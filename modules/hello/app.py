from flask import Blueprint, jsonify

bp = Blueprint('hello', __name__, url_prefix='/hello')


@bp.route('/')
def hello():
    return jsonify(message="Hello from module 'hello'.")


def init_module(app):
    """Optional initializer if a module prefers imperative registration."""
    app.register_blueprint(bp)
