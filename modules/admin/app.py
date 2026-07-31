from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import User


bp = Blueprint('admin', __name__, url_prefix='/admin')

ROLE_OPTIONS = {
	1: 'Normal',
	2: 'VIP',
	3: 'Moderator',
	10: 'Admin',
}


def _role_label(role: int | None) -> str:
	return ROLE_OPTIONS.get(role or 1, f'Rolle {role}')


def admin_required(view_func):
	@wraps(view_func)
	@login_required
	def wrapper(*args, **kwargs):
		if getattr(current_user, 'role', 1) != 10:
			abort(403)
		return view_func(*args, **kwargs)

	return wrapper


@bp.route('/')
@admin_required
def admin_nav():
	return render_template('admin/admin_nav.html')


@bp.route('/users', methods=['GET', 'POST'])
@admin_required
def admin_users():
	if request.method == 'POST':
		user_id = request.form.get('user_id', type=int)
		role = request.form.get('role', type=int)

		if user_id is None:
			flash('Ungültiger Benutzer.', 'error')
			return redirect(url_for('admin.admin_users'))

		if role not in ROLE_OPTIONS:
			flash('Ungültige Rolle.', 'error')
			return redirect(url_for('admin.admin_users'))

		user = db.session.get(User, user_id)
		if user is None:
			abort(404)

		if user.id == current_user.id and role != 10:
			flash('Du kannst deine eigene Admin-Rolle hier nicht entfernen.', 'error')
			return redirect(url_for('admin.admin_users'))

		old_role = user.role
		user.role = role
		db.session.commit()
		flash(
			f'Rolle für {user.username} von {_role_label(old_role)} auf {_role_label(role)} geändert.',
			'success',
		)
		return redirect(url_for('admin.admin_users'))

	users = User.query.order_by(User.id.asc()).all()
	return render_template('admin/admin_users.html', users=users, role_options=sorted(ROLE_OPTIONS.items()))


def init_module(app):
	app.register_blueprint(bp)
