from extensions import db
from flask_login import UserMixin
from flask import url_for
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
    avatar = db.Column(db.String(255))
    github_id = db.Column(db.String(100), unique=True, index=True)
    avatar_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    login_sessions = db.relationship('LoginSession', back_populates='user', lazy='dynamic',
                                      order_by='LoginSession.logged_in_at.desc()',
                                      cascade='all, delete-orphan')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def profile_image_url(self) -> str | None:
        """Return the GitHub avatar or the locally uploaded avatar URL."""
        if self.avatar:
            return url_for('static', filename=f'uploads/avatars/{self.avatar}')
        return self.avatar_url

    def __repr__(self) -> str:
        return f"<User {self.id} {self.username}>"


class ServerKey(db.Model):
    __tablename__ = 'server_keys'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    key_value = db.Column(db.String(255), unique=True, nullable=False, index=True)
    max_uses = db.Column(db.Integer, nullable=False, default=1, server_default=text('1'))
    uses_left = db.Column(db.Integer, nullable=False, default=1, server_default=text('1'))
    active = db.Column(db.Boolean, nullable=False, default=True, server_default=text('1'))
    # Temporary admin pause; the key becomes usable automatically afterwards.
    deactivated_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_currently_active(self) -> bool:
        """Return whether this key can be used right now."""
        return bool(
            self.active
            and (self.deactivated_until is None or self.deactivated_until <= datetime.utcnow())
        )

    def __repr__(self) -> str:
        return f"<ServerKey {self.id} {self.name} uses_left={self.uses_left}>"


class RegistrationSettings(db.Model):
    __tablename__ = 'registration_settings'
    id = db.Column(db.Integer, primary_key=True)
    server_keys_required = db.Column(db.Boolean, nullable=False, default=True, server_default=text('1'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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


class News(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    pinned = db.Column(db.Boolean, nullable=False, default=False, server_default=text('0'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = db.relationship('User', foreign_keys=[author_id])

    def __repr__(self) -> str:
        return f"<News {self.id} {self.title}>"
