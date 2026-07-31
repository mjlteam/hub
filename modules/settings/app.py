from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db

bp = Blueprint('settings', __name__, url_prefix='/settings')

@bp.route('/', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action', '')

        # Password change
        if action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            if not current_user.check_password(current_pw):
                flash('Aktuelles Passwort ist falsch.', 'error')
            elif len(new_pw) < 8:
                flash('Neues Passwort muss mindestens 8 Zeichen haben.', 'error')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Passwort erfolgreich geändert.', 'success')
            return redirect(url_for('settings.settings'))

    return render_template('settings/settings.html')


def init_module(app):
    app.register_blueprint(bp)
