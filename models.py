from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import text


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(200), unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Integer, nullable=False, default=1, server_default=text('1'))
    banned = db.Column(db.Boolean, nullable=False, default=False, server_default=text('0'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    login_sessions = db.relationship('LoginSession', back_populates='user', lazy='dynamic',
                                      order_by='LoginSession.logged_in_at.desc()')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.id} {self.username}>"


class LoginSession(db.Model):
    __tablename__ = 'login_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    browser = db.Column(db.String(80))
    browser_version = db.Column(db.String(20))
    os = db.Column(db.String(80))
    os_version = db.Column(db.String(20))
    device_type = db.Column(db.String(20))
    screen_width = db.Column(db.Integer)
    screen_height = db.Column(db.Integer)
    language = db.Column(db.String(10))
    logged_in_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = db.relationship('User', back_populates='login_sessions')

    def __repr__(self) -> str:
        return f"<LoginSession {self.id} user={self.user_id} at {self.logged_in_at}>"



