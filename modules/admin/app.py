from functools import wraps
import secrets

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from models import User, LoginSession, ServerKey


bp = Blueprint('admin', __name__, url_prefix='/admin')

ROLE_OPTIONS = {
	1: 'Normal',
	2: 'VIP',
	3: 'Moderator',
	10: 'Admin',
}


def _role_label(role: int | None) -> str:
	return ROLE_OPTIONS.get(role or 1, f'Rolle {role}')


def _generate_server_key() -> str:
	return secrets.token_urlsafe(24)


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
	server_keys = ServerKey.query.count()

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
		server_keys=server_keys,
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


@bp.route('/keys', methods=['GET', 'POST'])
@admin_required
def admin_keys():
	if request.method == 'POST':
		action = request.form.get('action', 'create')
		key_id = request.form.get('key_id', type=int)
		server_key = db.session.get(ServerKey, key_id) if key_id else None

		if action == 'delete':
			if server_key is None:
				abort(404)
			db.session.delete(server_key)
			db.session.commit()
			flash(f'Server-Key "{server_key.name}" wurde gelöscht.', 'success')
			return redirect(url_for('admin.admin_keys'))

		if action == 'toggle':
			if server_key is None:
				abort(404)
			server_key.active = not server_key.active
			db.session.commit()
			flash(f'Server-Key "{server_key.name}" wurde aktualisiert.', 'success')
			return redirect(url_for('admin.admin_keys'))

		name = (request.form.get('name') or '').strip()
		key_value = (request.form.get('key_value') or '').strip()
		max_uses = request.form.get('max_uses', type=int) or 1
		uses_left = request.form.get('uses_left', type=int)
		active = request.form.get('active') == 'on'

		if max_uses < 1:
			flash('Die maximale Nutzung muss mindestens 1 sein.', 'error')
			return redirect(url_for('admin.admin_keys'))

		if action == 'create':
			if not key_value:
				key_value = _generate_server_key()
			if not name:
				name = f'Server Key {key_value[:8]}'
			if ServerKey.query.filter_by(key_value=key_value).first():
				flash('Dieser Key-Wert existiert bereits.', 'error')
				return redirect(url_for('admin.admin_keys'))

			server_key = ServerKey(
				name=name,
				key_value=key_value,
				max_uses=max_uses,
				uses_left=max_uses,
				active=active,
			)
			db.session.add(server_key)
			db.session.commit()
			flash(f'Server-Key "{server_key.name}" wurde angelegt.', 'success')
			return redirect(url_for('admin.admin_keys'))

		if server_key is None:
			abort(404)

		if key_value and key_value != server_key.key_value:
			duplicate = ServerKey.query.filter(ServerKey.key_value == key_value, ServerKey.id != server_key.id).first()
			if duplicate:
				flash('Dieser Key-Wert existiert bereits.', 'error')
				return redirect(url_for('admin.admin_keys'))
			server_key.key_value = key_value

		if name:
			server_key.name = name
		server_key.max_uses = max_uses
		if uses_left is not None:
			server_key.uses_left = max(0, min(uses_left, max_uses))
		else:
			server_key.uses_left = min(server_key.uses_left, max_uses)
		server_key.active = active
		db.session.commit()
		flash(f'Server-Key "{server_key.name}" wurde gespeichert.', 'success')
		return redirect(url_for('admin.admin_keys'))

	server_keys = ServerKey.query.order_by(ServerKey.created_at.desc()).all()
	return render_template('admin/admin_keys.html', server_keys=server_keys)


def init_module(app):
	app.register_blueprint(bp)
