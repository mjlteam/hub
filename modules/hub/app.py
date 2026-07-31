from flask import Blueprint, render_template
from datetime import datetime
from flask_login import login_required

bp = Blueprint('hub', __name__, url_prefix='/')


@bp.route('/')
@login_required
def hub():
    return render_template('hub/hub.html', current_year=datetime.now().year)

def init_module(app):
    app.register_blueprint(bp)
