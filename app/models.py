from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timezone

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=True)
    password_hash = db.Column(db.String(256))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class RfidTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag_uid = db.Column(db.String(64), index=True, unique=True, nullable=False)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')

    def __repr__(self):
        return f'<RfidTag {self.username}>'

class AccessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag_uid = db.Column(db.String(64), index=True, nullable=False)
    username = db.Column(db.String(64), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), nullable=False, default='Negado')

    def __repr__(self):
        return f'<AccessLog {self.username} ({self.status}) at {self.timestamp}>'