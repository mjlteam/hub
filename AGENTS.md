# Agent Markdown — MJL Hub

Guidelines for AI agents and contributors working in this repository.

## Project Overview

Modular Flask application ("Hub") for the MJL-Team: a small team portal with
authentication, admin user/key management, settings and a News/Blog module.

## Tech Stack

- **Python 3.10+** (tested with 3.12), **Flask**, **SQLite** (via Flask-SQLAlchemy)
- **Flask-Login** for sessions, **Werkzeug** for password hashing
- **htmx** (partial page loads), **Alpine.js** (interactivity), **Tailwind CDN** + custom `design.css`
- Virtualenv: `.venv` (use `.venv/bin/python` for all commands)

## Design

- **Always read `./DESIGN.md` first.** It defines the design tokens, colors, typography, spacing and component styles.
- Use design tokens (CSS custom properties like `--ink`, `--teal`, `--blue`, `--surface-*`) instead of hardcoded hex values.
- **Blue accent family** (`--blue`, `--blue-deep`, `--blue-soft`, `--blue-soft-hover`) is the interactive/navigation accent (active nav tab, news eyebrows, pinned pills). Teal stays the brand color.
- Do not introduce new design outside the Design guidelines. Ask for clarification on design decisions.

## Project Structure

```
run.py                  # App factory, module loader, error handlers, config
models.py               # SQLAlchemy models (User, LoginSession, News)
extensions.py           # db, login_manager instances
modules.json            # Module registry (enabled/disabled)
modules/<name>/app.py   # Each module: `bp = Blueprint(...)` + `init_module(app)`
templates/<name>/…      # Templates, one folder per module (extends base.html)
static/css/design.css   # Design system / tokens
scripts/init_db.py      # DB init (create_all) + admin seed
```

## Conventions

- **Modules:** register new modules in `modules.json` (`{"name": ..., "package": "modules.<name>", "enabled": true}`). Each module exposes a `bp` Blueprint and/or `init_module(app)`.
- **Auth/roles:** `current_user.role` — `1` Normal, `2` VIP, `3` Moderator, `10` Admin. Admin-only views use `abort(403)` on `role != 10` or a `@admin_required` decorator.
- **DB access:** use `db.session.get(Model, id)` — never the deprecated `Model.query.get(id)`.
- **Queries:** use `Model.query` / `db.session.query` with filters; new tables are created automatically by `create_all()` on startup — no manual migrations.
- **Templates:** extend `base.html`, fill `{% block title %}` and `{% block content %}`. German UI text. Use `url_for(...)` everywhere, never hardcoded URLs.
- **htmx:** sidebar links use `hx-get` + `hx-target="#main-content"` + `hx-swap="innerHTML"` + `hx-push-url="true"`. `base.html` handles HX-Requests by rendering only the content block.
- **Alpine.js:** component state via `x-data`, toggles with `x-show` + `x-cloak` (so content is hidden before Alpine loads).
- **Flash messages:** `flash(msg, 'success' | 'error' | 'warning')` — rendered by `templates/toasts.html` (auto-included in `base.html`).
- **XSS safety:** never inline user content into JS strings. Use `|tojson` in `onclick`/`onsubmit` handlers (HTML-escaped JSON); Jinja auto-escapes normal template output.
- **Code style:** 4-space indentation (new files); PEP 8 naming. Keep changes minimal and reuse existing helpers.

## Running & Testing

```bash
.venv/bin/python scripts/init_db.py          # create tables (+ --seed for admin/admin123)
.venv/bin/python run.py                      # start on :5000 (init_db runs automatically)
.venv/bin/python -m py_compile <file.py>     # syntax check
```

- Default test account: `admin` / `admin123` (role 10) — only after `init_db.py --seed`.
- After template/CSS changes, restart the server (auto-reload templates is enabled, Python changes need a restart).

## Workflow for Agents

1. Read `DESIGN.md`, `AGENTS.md`, and the surrounding code/templates before editing.
2. Ask for clarification on design decisions or critical changes.
3. Verify changes: syntax check, restart the app, curl the affected routes.
4. Keep the final summary short.
