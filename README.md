# hub

Kurze Projektbeschreibung
-------------------------
Dies ist eine modulare Flask-Anwendung (Python). Sie bietet:

- Lokale Benutzer-Authentifizierung (`Flask-Login`) mit datenbankgestützter Registrierung/Login.
- SQLite (standardmäßig `sqlite:///main.db`) als Entwicklungsdatenbank.
- Modulares Blueprint-System: Module werden über `modules.json` geladen.
- Leichtes Design-Framework (Tailwind-Prototyping + eigenes CSS) und interaktive Helfer (`htmx`, `Alpine.js`).

Voraussetzungen
---------------
- Python 3.10+ (getestet mit 3.12)
- `pip` zum Installieren der Abhängigkeiten
- Optional: `git`, wenn die Versions-ID im Footer angezeigt werden soll

Installation
------------
1. Virtuelle Umgebung erstellen und aktivieren:

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
```

2. Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

Konfiguration (.env)
--------------------
Kopiere `.env.example` zu `.env` und passe Werte an. Wichtige Variablen:

- `SECRET_KEY` — sollte für Produktion ein sicherer, zufälliger Wert sein.
- `DATABASE_URL` — z. B. `sqlite:///main.db` oder eine PostgreSQL-URL.
- `GITHUB_CLIENT_ID` und `GITHUB_CLIENT_SECRET` — Zugangsdaten der GitHub OAuth App.
- `GITHUB_REDIRECT_URI` — exakt `http://localhost:5000/auth/github/callback`, ohne abschließenden Slash.

Für lokale OAuth-Entwicklung muss die Callback-URL der GitHub-App exakt
`http://localhost:5000/auth/github/callback` lauten. Vor dem ersten Start
werden Tabellen und additive Schema-Upgrades ausgeführt:

```bash
python scripts/init_db.py
```

Datenbank initialisieren
------------------------
Ein Hilfsskript ist vorhanden, das Tabellen anlegt oder löscht:

```bash
python scripts/init_db.py        # erstellt Tabellen
python scripts/init_db.py --drop # löscht alle Tabellen und erstellt sie neu
```

Starten der App
---------------
Entwicklungsmodus (lokal):

```bash
python scripts/init_db.py
python run.py --debug
```

Die App läuft dabei auf `http://localhost:5000/`. Die registrierte GitHub-Callback-URL
und `GITHUB_REDIRECT_URI` müssen exakt `http://localhost:5000/auth/github/callback`
sein — ohne abschließenden Slash. Wenn du die App über `127.0.0.1` öffnest, bleibt die
OAuth-Redirect-URI trotzdem bewusst `localhost`; beide Werte dürfen nicht vermischt werden.

Module
------
Module werden über `modules.json` konfiguriert. Beispielstruktur eines Moduls:

- `modules/<name>/app.py` — sollte entweder ein `Blueprint` als `bp` exportieren oder eine Funktion `init_module(app)` bereitstellen.

Beispiel `modules.json`:

```json
{
    "modules": [
        { "package": "modules.hub", "enabled": true },
        { "package": "modules.auth", "enabled": true }
    ]
}
```

Authentifizierung
------------------
Das Projekt verwendet lokale Authentifizierung mit `Flask-Login` und einem `User`-Modell (Passwort-Hashes). Folgende Routen sind vorhanden:

- `/auth/register` — Registrierung
- `/auth/login` — Anmeldung
- `/auth/login/github` — GitHub OAuth Login
- `/auth/github/callback` — GitHub OAuth Callback
- `GET /auth/logout` — kompatible Abmelde-Bestätigung für alte Links
- `POST /auth/logout` — tatsächliche Abmeldung mit Session-CSRF-Token

Der OAuth-State wird von Authlib in der Flask-Session verwaltet. Die Callback-Behandlung
fragt das GitHub-Profil und `/user/emails` ab und akzeptiert nur eine primäre, verifizierte
E-Mail-Adresse. Ohne nutzbare E-Mail wird kein Konto angelegt. Existiert noch kein lokales
Konto, wird GitHub nicht automatisch angelegt: Die Registrierung wird mit dem Server-Key-Gate
fortgesetzt und das GitHub-Profil erst nach ausdrücklicher Kontoerstellung verknüpft.

Server-Keys werden unter `/admin/keys` verwaltet. Administratoren können dort einzelne Keys
aktivieren/deaktivieren und global festlegen, ob neue Registrierungen einen aktiven Key brauchen.
Auf einer frischen Installation ist diese Pflicht standardmäßig aktiv; ein Administrator muss
zuerst einen Key anlegen oder die Pflicht im Server-Key-Menü deaktivieren. Der GitHub-Login leitet
bei aktiver Pflicht ebenfalls zuerst zum Server-Key-Menü weiter.

Design & Templates
------------------
Die Basisvorlage ist `templates/base.html`. Styles liegen in `static/css/design.css`. Logos befinden sich in `static/logo/`.

Fehlerseiten
------------
Eigene Fehlerseiten sind unter `templates/errors/` (400, 403, 404, 500).
