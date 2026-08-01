from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from extensions import db
from models import News


bp = Blueprint('news', __name__, url_prefix='/news')


@bp.route('/', methods=['GET', 'POST'])
@login_required
def news():
    # --- Admin actions (Erstellen / Bearbeiten / Anheften / Löschen) ---
    if request.method == 'POST':
        if current_user.role != 10:
            abort(403)

        action = request.form.get('action', 'create')
        news_id = request.form.get('news_id', type=int)
        item = db.session.get(News, news_id) if news_id else None

        if action == 'delete':
            if item is None:
                abort(404)
            title = item.title
            db.session.delete(item)
            db.session.commit()
            flash(f'News "{title}" wurde gelöscht.', 'success')
            return redirect(url_for('news.news'))

        if action == 'toggle':
            if item is None:
                abort(404)
            item.pinned = not item.pinned
            db.session.commit()
            flash(
                f'News "{item.title}" ist jetzt '
                f'{"angeheftet" if item.pinned else "nicht mehr angeheftet"}.',
                'success',
            )
            return redirect(url_for('news.news'))

        if action == 'update':
            if item is None:
                abort(404)
            title = (request.form.get('title') or '').strip()
            content = (request.form.get('content') or '').strip()
            if not title or not content:
                flash('Titel und Inhalt dürfen nicht leer sein.', 'error')
                return redirect(url_for('news.news'))
            item.title = title
            item.content = content
            item.pinned = request.form.get('pinned') == 'on'
            db.session.commit()
            flash(f'News "{item.title}" wurde gespeichert.', 'success')
            return redirect(url_for('news.news'))

        # --- Create ---
        title = (request.form.get('title') or '').strip()
        content = (request.form.get('content') or '').strip()
        if not title or not content:
            flash('Titel und Inhalt dürfen nicht leer sein.', 'error')
            return redirect(url_for('news.news'))

        item = News(
            title=title,
            content=content,
            author_id=current_user.id,
            pinned=request.form.get('pinned') == 'on',
        )
        db.session.add(item)
        db.session.commit()
        flash(f'News "{item.title}" wurde veröffentlicht.', 'success')
        # Skeleton nur direkt nach dem Veröffentlichen eines neuen Beitrags zeigen
        session['news_just_created'] = True
        return redirect(url_for('news.news'))

    # Flag wird beim nächsten GET konsumiert (einmalig, kein Dauer-Skeleton)
    show_skeleton = session.pop('news_just_created', False)
    items = News.query.order_by(News.pinned.desc(), News.created_at.desc()).all()
    reading_minutes_map = {item.id: _reading_minutes(item) for item in items}
    return render_template(
        'news/news.html',
        items=items,
        reading_minutes_map=reading_minutes_map,
        show_skeleton=show_skeleton,
    )


def _reading_minutes(item: News) -> int:
    """Grobe Lesezeit in Minuten (~200 Wörter pro Minute)."""
    words = len((item.content or '').split())
    return max(1, round(words / 200))


@bp.route('/<int:news_id>/')
@login_required
def post(news_id):
    item = db.session.get(News, news_id)
    if item is None:
        abort(404)

    # Chronologische Reihenfolge für Prev/Next-Navigation (neueste zuerst)
    ordered = News.query.order_by(News.created_at.desc()).all()
    idx = next((i for i, n in enumerate(ordered) if n.id == item.id), None)
    prev_item = ordered[idx + 1] if idx is not None and idx + 1 < len(ordered) else None
    next_item = ordered[idx - 1] if idx is not None and idx > 0 else None

    # Verwandte Artikel: neueste 3 ohne den aktuellen
    related = [n for n in ordered if n.id != item.id][:3]

    return render_template(
        'news/post.html',
        item=item,
        prev_item=prev_item,
        next_item=next_item,
        related=related,
        reading_minutes=_reading_minutes(item),
    )


def init_module(app):
    app.register_blueprint(bp)
