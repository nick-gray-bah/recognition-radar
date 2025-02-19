from app import db
import datetime


class Target(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.String(80), unique=True, nullable=False)
    target_name = db.Column(db.String(120), nullable=False)
    embedding = db.Column(db.PickleType, nullable=False)
    image_path = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            'target_id': self.target_id,
            'embedding': self.embedding,
            'image_path': self.image_path
        }


class Stream(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    stream_id = db.Column(db.String(255), unique=True, nullable=False)
    stream_url = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)
    started_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'stream_id': self.stream_id,
            'stream_url': self.stream_url,
            'active': self.active,
            'started_at': self.started_at.isoformat()
        }


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_name = db.Column(db.String(120), unique=True, nullable=False)
    contact_email = db.Column(db.String(120), unique=True, nullable=True)
    contact_phone = db.Column(db.String(120), unique=True, nullable=True)
    active = db.Column(db.Boolean, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'active': self.active
        }
