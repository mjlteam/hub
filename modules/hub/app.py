from flask import Blueprint, render_template
from datetime import datetime

bp = Blueprint('hub', __name__, url_prefix='/')


@bp.route('/')
def hub():
    return render_template('hub/hub.html')


def init_module(app):
    app.register_blueprint(bp)
