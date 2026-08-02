from flask import Blueprint, render_template
from datetime import datetime
from modules.auth.decorators import login_required

from models import News

bp = Blueprint('hub', __name__, url_prefix='/')


def _render_hub():
    latest_news = News.query.order_by(News.pinned.desc(), News.created_at.desc()).limit(3).all()
    return render_template(
        'hub/hub.html',
        current_year=datetime.now().year,
        latest_news=latest_news,
    )


@bp.route('/')
@login_required
def hub():
    return _render_hub()


@bp.route('/dashboard')
@login_required
def dashboard():
    return _render_hub()

def init_module(app):
    app.register_blueprint(bp)
