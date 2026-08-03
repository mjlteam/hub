import secrets
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user
from modules.auth.decorators import login_required
from modules.auth.csrf import csrf_protect
from modules.auth.app import validate_password
from PIL import Image, UnidentifiedImageError

from extensions import db

bp = Blueprint('settings', __name__, url_prefix='/settings')

# --- Avatar constants ---
AVATAR_ALLOWED = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
AVATAR_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
AVATAR_SIZE = 256


def _avatar_dir() -> Path:
    return Path(current_app.root_path) / 'static' / 'uploads' / 'avatars'


def _save_avatar(file_storage) -> str:
    """Validate, square-crop and re-encode an uploaded avatar. Returns the new filename."""
    filename = file_storage.filename or ''
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in AVATAR_ALLOWED:
        raise ValueError('Nur JPG, PNG, WebP oder GIF erlaubt.')

    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > AVATAR_MAX_BYTES:
        raise ValueError('Bild darf maximal 5 MB groß sein.')

    try:
        img = Image.open(file_storage.stream)
    except Image.DecompressionBombError:
        raise ValueError('Bild ist zu groß (max. 4096 × 4096 Pixel).')
    except (UnidentifiedImageError, OSError):
        raise ValueError('Keine gültige Bilddatei.')

    # Decompression-bomb guard: reject huge dimensions before decoding
    width, height = img.size
    if width * height > 4096 * 4096:
        raise ValueError('Bild ist zu groß (max. 4096 × 4096 Pixel).')

    try:
        img.load()
    except (UnidentifiedImageError, OSError):
        raise ValueError('Keine gültige Bilddatei.')

    # Center square crop, then downscale — keep RGBA so transparent PNGs stay transparent
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2, (w - side) // 2 + side, (h - side) // 2 + side))
    img = img.convert('RGBA').resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)

    _avatar_dir().mkdir(parents=True, exist_ok=True)
    name = f'avatar_{secrets.token_hex(8)}.png'
    img.save(_avatar_dir() / name, 'PNG')
    return name

@bp.route('/', methods=['GET', 'POST'])
@csrf_protect
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action', '')

        # Avatar upload
        if action == 'upload_avatar':
            file = request.files.get('avatar')
            if file is None or not file.filename:
                flash('Bitte eine Bilddatei auswählen.', 'error')
                return redirect(url_for('settings.settings'))
            try:
                new_name = _save_avatar(file)
            except ValueError as e:
                flash(str(e), 'error')
                return redirect(url_for('settings.settings'))
            # Delete the old avatar file
            if current_user.avatar:
                old = _avatar_dir() / current_user.avatar
                if old.exists():
                    old.unlink()
            current_user.avatar = new_name
            db.session.commit()
            flash('Profilbild aktualisiert.', 'success')
            return redirect(url_for('settings.settings'))

        # Avatar remove
        if action == 'remove_avatar':
            if current_user.avatar:
                old = _avatar_dir() / current_user.avatar
                if old.exists():
                    old.unlink()
                current_user.avatar = None
                db.session.commit()
                flash('Profilbild entfernt.', 'success')
            return redirect(url_for('settings.settings'))

        # Password change
        if action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            if not current_user.check_password(current_pw):
                flash('Aktuelles Passwort ist falsch.', 'error')
            else:
                valid, reasons = validate_password(new_pw, current_user.username)
                if not valid:
                    flash('Passwort entspricht nicht der Sicherheitsrichtlinie: ' + '; '.join(reasons), 'error')
                    return redirect(url_for('settings.settings'))
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Passwort erfolgreich geändert.', 'success')
            return redirect(url_for('settings.settings'))

    return render_template('settings/settings.html')


def init_module(app):
    app.register_blueprint(bp)
