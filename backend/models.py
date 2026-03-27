import json

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(120), default="General")
    difficulty_pref = db.Column(db.String(20), default="medium")
    performance_json = db.Column(db.Text, default="{}")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "subject": self.subject,
            "difficulty_pref": self.difficulty_pref,
            "performance": json.loads(self.performance_json or "{}"),
        }


class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "body": self.body}


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey("content.id"), nullable=False)
    qtype = db.Column(db.String(50), nullable=False)
    question = db.Column(db.Text, nullable=False)
    options_json = db.Column(db.Text, default="[]")
    answer = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    source = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "content_id": self.content_id,
            "qtype": self.qtype,
            "question": self.question,
            "options": json.loads(self.options_json or "[]"),
            "answer": self.answer,
            "difficulty": self.difficulty,
            "source": self.source,
        }


class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    response_time_ms = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, nullable=False)
