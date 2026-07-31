from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from models import User, LoginSession


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
def admin_dashboard():
    total_users = User.query.count()
    total_sessions = LoginSession.query.count()
    recent_sessions = LoginSession.query.order_by(LoginSession.logged_in_at.desc()).limit(20).all()
    admins = User.query.filter_by(role=10).count()

    # Per-browser stats
    browser_stats = db.session.query(
        LoginSession.browser, func.count(LoginSession.id).label('cnt')
    ).group_by(LoginSession.browser).order_by(func.count(LoginSession.id).desc()).all()

    # Per-device stats
    device_stats = db.session.query(
        LoginSession.device_type, func.count(LoginSession.id).label('cnt')
    ).group_by(LoginSession.device_type).order_by(func.count(LoginSession.id).desc()).all()

    return render_template(
        'admin/admin_dashboard.html',
        total_users=total_users,
        total_sessions=total_sessions,
        admins=admins,
        recent_sessions=recent_sessions,
        browser_stats=browser_stats,
        device_stats=device_stats,
    )

@bp.route('/users', methods=['GET', 'POST'])
@admin_required
def admin_users():
	if request.method == 'POST':
		user_id = request.form.get('user_id', type=int)
		action = request.form.get('action', 'role')

		user = db.session.get(User, user_id)
		if user is None:
			abort(404)

		# --- Ban / Unban ---
		if action == 'ban':
			if user.id == current_user.id:
				flash('Du kannst dich nicht selbst bannen.', 'error')
				return redirect(url_for('admin.admin_users'))
			user.banned = True
			db.session.commit()
			flash(f'{user.username} wurde gesperrt.', 'success')
			return redirect(url_for('admin.admin_users'))

		if action == 'unban':
			user.banned = False
			db.session.commit()
			flash(f'{user.username} wurde entsperrt.', 'success')
			return redirect(url_for('admin.admin_users'))

		# --- Password change ---
		if action == 'password':
			new_pw = request.form.get('new_password', '')
			if len(new_pw) < 8:
				flash('Passwort muss mindestens 8 Zeichen haben.', 'error')
				return redirect(url_for('admin.admin_users'))
			user.set_password(new_pw)
			db.session.commit()
			flash(f'Passwort für {user.username} geändert.', 'success')
			return redirect(url_for('admin.admin_users'))

		# --- Role change ---
		role = request.form.get('role', type=int)
		if role not in ROLE_OPTIONS:
			flash('Ungültige Rolle.', 'error')
			return redirect(url_for('admin.admin_users'))

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

	# Search / filter
	search = (request.args.get('q') or '').strip()
	query = User.query
	if search:
		like = f'%{search}%'
		query = query.filter((User.username.ilike(like)) | (User.email.ilike(like)))

	users = query.order_by(User.id.asc()).all()

	# Load login sessions for all visible users and deduplicate by unique device
	# (browser + os + device_type), keeping only the most recent per device
	user_ids = [u.id for u in users]
	devices_by_user = {}
	if user_ids:
		all_sessions = LoginSession.query.filter(
			LoginSession.user_id.in_(user_ids)
		).order_by(LoginSession.logged_in_at.desc()).all()

		for s in all_sessions:
			# Deduplicate: unique key = (browser, os, device_type)
			key = (s.browser or '', s.os or '', s.device_type or '')
			dlist = devices_by_user.setdefault(s.user_id, {})
			if key not in dlist:
				dlist[key] = s

	# Convert dedup dict to sorted list per user (newest first)
	sessions_by_user = {}
	for uid, dmap in devices_by_user.items():
		sessions_by_user[uid] = sorted(dmap.values(), key=lambda s: s.logged_in_at or 0, reverse=True)

	return render_template(
		'admin/admin_users.html',
		users=users,
		role_options=sorted(ROLE_OPTIONS.items()),
		search=search,
		sessions_by_user=sessions_by_user,
	)


def init_module(app):
	app.register_blueprint(bp)
