# hub

Kurze Projektbeschreibung
-------------------------
Dies ist eine modulare Flask-Anwendung (Python). Sie bietet:

- Lokale Benutzer-Authentifizierung (`Flask-Login`) mit datenbankgestützter Registrierung/Login.
- SQLite (standardmäßig `sqlite:///main.db`) als Entwicklungsdatenbank.
- Modulares Blueprint‑System: Module werden über `modules.json` geladen.
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
python run.py --debug
```

Die App läuft standardmäßig auf `http://127.0.0.1:5000/`.

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
- `/auth/logout` — Abmeldung

Design & Templates
------------------
Die Basisvorlage ist `templates/base.html`. Styles liegen in `static/css/design.css`. Logos befinden sich in `static/logo/`.

Fehlerseiten
------------
Eigene Fehlerseiten sind unter `templates/errors/` (400, 403, 404, 500).

Weiteres / Entwicklung
----------------------
- CSRF‑Schutz, E-Mail‑Verifikation und Passwort‑Reset sind nicht standardmäßig aktiviert — können bei Bedarf ergänzt werden.
- Unit- oder Integrationstests sollten in einem späteren Schritt hinzugefügt werden.

Hilfe / Kontakt
---------------
Wenn du Änderungen am Modul-Loader, an der Auth-Logik oder am Design wünschst, sag mir welche Funktion du erweitert haben möchtest — ich mache es direkt im Projekt.

