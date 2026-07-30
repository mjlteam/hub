from flask import Blueprint, jsonify

bp = Blueprint('hub', __name__, url_prefix='/hub')


@bp.route('/')
def hub():
    return "There is nothing in here right now"


def init_module(app):
    app.register_blueprint(bp)
