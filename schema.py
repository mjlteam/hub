"""Small, additive database upgrades needed by the running application."""

from sqlalchemy import inspect, text

from extensions import db


_USER_COLUMNS = {
    "role": "ALTER TABLE users ADD COLUMN role INTEGER NOT NULL DEFAULT 1",
    "banned": "ALTER TABLE users ADD COLUMN banned BOOLEAN NOT NULL DEFAULT 0",
    "avatar": "ALTER TABLE users ADD COLUMN avatar VARCHAR(255)",
    "github_id": "ALTER TABLE users ADD COLUMN github_id VARCHAR(100)",
    "avatar_url": "ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)",
}

_SERVER_KEY_COLUMNS = {
    "deactivated_until": "ALTER TABLE server_keys ADD COLUMN deactivated_until DATETIME",
}


def ensure_database_schema(app) -> None:
    """Create missing tables/columns and enforce nullable unique user fields.

    This is intentionally additive for the existing SQLite deployment. It fails
    loudly when old data contains duplicates rather than silently weakening the
    uniqueness guarantees declared by the models.
    """
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        if "users" not in inspector.get_table_names():
            _ensure_registration_settings()
            return

        _ensure_registration_settings()

        columns = {column["name"] for column in inspector.get_columns("users")}
        for name, statement in _USER_COLUMNS.items():
            if name not in columns:
                db.session.execute(text(statement))
                db.session.commit()

        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())
        if "server_keys" in table_names:
            server_key_columns = {column["name"] for column in inspector.get_columns("server_keys")}
            for name, statement in _SERVER_KEY_COLUMNS.items():
                if name not in server_key_columns:
                    db.session.execute(text(statement))
                    db.session.commit()

        for column, index_name in (("email", "ix_users_email"), ("github_id", "ix_users_github_id")):
            _ensure_unique_index(column, index_name)


def _ensure_registration_settings() -> None:
    """Create the singleton settings row with server keys required by default."""
    db.session.execute(text(
        "INSERT INTO registration_settings (id, server_keys_required) "
        "SELECT 1, 1 WHERE NOT EXISTS "
        "(SELECT 1 FROM registration_settings WHERE id = 1)"
    ))
    db.session.commit()


def _ensure_unique_index(column: str, index_name: str) -> None:
    """Ensure a single-column unique index without hiding duplicate values."""
    inspector = inspect(db.engine)
    indexes = {index["name"]: index for index in inspector.get_indexes("users")}
    current = indexes.get(index_name)
    if current and current.get("unique") and current.get("column_names") == [column]:
        return
    if current:
        db.session.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
        db.session.commit()

    duplicates = db.session.execute(text(
        f"SELECT {column} FROM users WHERE {column} IS NOT NULL "
        f"GROUP BY {column} HAVING COUNT(*) > 1"
    )).fetchall()
    if duplicates:
        values = ", ".join(repr(row[0]) for row in duplicates[:3])
        raise RuntimeError(
            f"Cannot create unique users.{column} index; duplicate values exist: {values}"
        )

    db.session.execute(text(
        f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON users ({column})"
    ))
    db.session.commit()
