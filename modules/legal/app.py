from flask import Blueprint, render_template

bp = Blueprint('legal', __name__, url_prefix='/legal')


@bp.route('/')
def terms():
    """Render the Terms of Service (Nutzungsbedingungen) page."""
    return render_template('legal/legal.html')


def init_module(app):
    app.register_blueprint(bp)
