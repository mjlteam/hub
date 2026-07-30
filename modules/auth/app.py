from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from extensions import db
from models import User
import re

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        if user and user.check_password(password):
            login_user(user)
            next_url = request.args.get('next') or request.form.get('next')
            return redirect(next_url or url_for('hub.hub'))
        flash('Ungültiger Benutzername oder Passwort', 'error')
    next_url = request.args.get('next')
    return render_template('auth/login.html', next=next_url)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if not username or not password:
            flash('Benutzername und Passwort sind erforderlich', 'error')
            return render_template('auth/register.html')
        # Password policy check
        valid, reasons = validate_password(password, username)
        if not valid:
            flash('Passwort entspricht nicht der Sicherheitsrichtlinie: ' + '; '.join(reasons), 'error')
            return render_template('auth/register.html')
        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben', 'error')
            return render_template('auth/register.html')
        if email and User.query.filter_by(email=email).first():
            flash('E-Mail bereits registriert', 'error')
            return render_template('auth/register.html')
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('hub.hub'))
    return render_template('auth/register.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


def init_module(app):
    app.register_blueprint(bp)


def validate_password(password: str, username: str | None = None):
    """Validate password against simple policy.

    Returns (bool, list_of_reasons). Reasons are human-readable strings.
    """
    reasons = []
    if not password or len(password) < 8:
        reasons.append('mindestens 8 Zeichen')
    if not re.search(r'[A-Z]', password):
        reasons.append('mindestens ein Großbuchstabe')
    if not re.search(r'[a-z]', password):
        reasons.append('mindestens ein Kleinbuchstabe')
    if not re.search(r'\d', password):
        reasons.append('mindestens eine Ziffer')
    if not re.search(r'[!@#$%^&*()_+\-=[\]{};:\\\\|,.<>\/?]', password):
        reasons.append('mindestens ein Sonderzeichen, z.B. !@#$%')
    if username:
        try:
            if username.strip() and username.lower() in password.lower():
                reasons.append('das Passwort darf den Benutzernamen nicht enthalten')
        except Exception:
            pass
    return (len(reasons) == 0, reasons)
