"""Database initialization helper.

Usage:
  python scripts/init_db.py          # create tables
  python scripts/init_db.py --drop   # drop all tables then create

This script loads the app configuration (including `.env`) and runs
SQLAlchemy `create_all()` / `drop_all()` within the app context.
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path so `from run import create_app` works
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from run import create_app
from extensions import db
from sqlalchemy import inspect, text


def ensure_user_role_column():
    inspector = inspect(db.engine)
    if 'users' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('users')}
    if 'role' in columns:
        return

    print('Adding missing users.role column...')
    db.session.execute(text('ALTER TABLE users ADD COLUMN role INTEGER NOT NULL DEFAULT 1'))
    db.session.commit()


def main():
    parser = argparse.ArgumentParser(description='Initialize or reset the database')
    parser.add_argument('--drop', action='store_true', help='Drop all tables before creating')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.drop:
            confirm = input('This will DROP ALL TABLES in the configured database. Type "yes" to proceed: ')
            if confirm.lower() != 'yes':
                print('Aborted.')
                return
            print('Dropping all tables...')
            db.drop_all()

        print('Creating tables...')
        db.create_all()
        ensure_user_role_column()
        print('Done.')


if __name__ == '__main__':
    main()
