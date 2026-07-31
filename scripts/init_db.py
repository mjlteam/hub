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


def ensure_user_columns():
    inspector = inspect(db.engine)
    if 'users' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('users')}
    if 'role' not in columns:
        print('Adding missing users.role column...')
        db.session.execute(text('ALTER TABLE users ADD COLUMN role INTEGER NOT NULL DEFAULT 1'))
        db.session.commit()

    if 'banned' not in columns:
        print('Adding missing users.banned column...')
        db.session.execute(text('ALTER TABLE users ADD COLUMN banned BOOLEAN NOT NULL DEFAULT 0'))
        db.session.commit()



def seed_admin():
    """Create or update the default admin/test account."""
    from models import User
    admin = User.query.filter_by(username='admin').first()
    if admin:
        admin.role = 10
        print('Updated existing admin user → role=10 (Admin)')
    else:
        admin = User(username='admin', email='admin@mjlteam.de', role=10)
        admin.set_password('admin123')
        db.session.add(admin)
        print('Created admin user: admin / admin123 (role=10)')
    db.session.commit()


def main():
    parser = argparse.ArgumentParser(description='Initialize or reset the database')
    parser.add_argument('--drop', action='store_true', help='Drop all tables before creating')
    parser.add_argument('--seed', action='store_true', help='Create/update admin test account (admin / admin123, role=10)')
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
        ensure_user_columns()

        if args.seed:
            seed_admin()

        print('Done.')


if __name__ == '__main__':
    main()
