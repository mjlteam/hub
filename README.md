# hub
#Tech Stack
Backend    Flask (Python)
Datenbank    SQLite
Auth    Flask-Login + Authlib (OAuth)
Styling    Tailwind CSS
Interaktivität    htmx + Alpine.js

## Modular App Structure

This project supports modular Flask apps. Modules are declared in `modules.json` at the project root. Each module should be a package (for example `modules/<name>/app.py`) and expose either:

- a `bp` Flask `Blueprint` variable, or
- an `init_module(app)` function which performs registration.

Example module: `modules/hello/app.py` exposes a `bp` at the `/hello` prefix. Add new modules by updating `modules.json` with the module `package` (e.g. `modules.my_module`).

