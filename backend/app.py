import json
import os
import re
import time
from datetime import datetime

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
)
from werkzeug.security import check_password_hash, generate_password_hash
from PyPDF2 import PdfReader
from sqlalchemy import text as sql_text

from models import db, User, Content, Question, Attempt
from quiz_engine import generate_questions, suggest_difficulty


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.join(BASE_DIR, "static"),
        template_folder=os.path.join(BASE_DIR, "templates"),
    )
    CORS(app)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'quiz_ai.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.environ.get(
        "JWT_SECRET_KEY", "dev-secret-change-me"
    )

    db.init_app(app)
    JWTManager(app)

    with app.app_context():
        db.create_all()
        with db.engine.connect() as conn:
            cols = [row[1] for row in conn.execute(sql_text("PRAGMA table_info(question)"))]
            if "source" not in cols:
                conn.execute(sql_text("ALTER TABLE question ADD COLUMN source TEXT"))
                conn.commit()

    def ensure_user(optional=True):
        if optional:
            verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            return User.query.get(user_id), None
        user = User.query.filter_by(email="guest@local").first()
        if not user:
            user = User(
                email="guest@local",
                password_hash=generate_password_hash("guest"),
                subject="General",
                difficulty_pref="medium",
                performance_json=json.dumps({"attempts": 0, "correct": 0}),
            )
            db.session.add(user)
            db.session.commit()
        token = create_access_token(identity=user.id)
        return user, token

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/auth/register")
    def register():
        payload = request.get_json(silent=True) or {}
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Account already exists."}), 400

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            subject=payload.get("subject") or "General",
            difficulty_pref=payload.get("difficulty_pref") or "medium",
            performance_json=json.dumps({"attempts": 0, "correct": 0}),
        )
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=user.id)
        return jsonify({"token": token, "user": user.to_dict()})

    @app.post("/api/auth/login")
    def login():
        payload = request.get_json(silent=True) or {}
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid credentials."}), 401
        token = create_access_token(identity=user.id)
        return jsonify({"token": token, "user": user.to_dict()})

    @app.get("/api/profile")
    @jwt_required()
    def get_profile():
        user = User.query.get_or_404(get_jwt_identity())
        return jsonify(user.to_dict())

    @app.put("/api/profile")
    @jwt_required()
    def update_profile():
        user = User.query.get_or_404(get_jwt_identity())
        payload = request.get_json(silent=True) or {}
        user.subject = payload.get("subject") or user.subject
        user.difficulty_pref = payload.get("difficulty_pref") or user.difficulty_pref
        db.session.commit()
        return jsonify(user.to_dict())

    @app.post("/api/content")
    def upload_content():
        verify_jwt_in_request(optional=True)
        payload = request.get_json(silent=True) or {}
        text = (payload.get("text") or "").strip()
        title = (payload.get("title") or "").strip() or "Untitled Content"
        if len(text) < 20:
            return jsonify({"error": "Please provide at least 20 characters."}), 400
        printable = sum(ch.isprintable() for ch in text)
        if printable / max(len(text), 1) < 0.85:
            return (
                jsonify(
                    {"error": "Content looks unreadable. Please paste clean text."}
                ),
                400,
            )

        user, token = ensure_user(optional=True)
        user_id = user.id

        content = Content(user_id=user_id, title=title, body=text)
        db.session.add(content)
        db.session.commit()
        payload = content.to_dict()
        if token and user:
            payload["token"] = token
            payload["user"] = user.to_dict()
        return jsonify(payload)

    @app.post("/api/content/upload")
    def upload_content_file():
        user, token = ensure_user(optional=True)
        if "file" not in request.files:
            return jsonify({"error": "File missing."}), 400
        file = request.files["file"]
        filename = (file.filename or "").lower()
        if not filename.endswith(".pdf"):
            return jsonify({"error": "Only PDF files are supported."}), 400
        try:
            reader = PdfReader(file)
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            text = "\n".join(text_parts).strip()
        except Exception as exc:
            return jsonify({"error": f"Failed to read PDF: {exc}"}), 400
        if len(text) < 20:
            return (
                jsonify(
                    {"error": "No readable text found in the PDF. Please paste text."}
                ),
                400,
            )
        content = Content(
            user_id=user.id,
            title=(request.form.get("title") or "Uploaded PDF").strip(),
            body=text,
        )
        db.session.add(content)
        db.session.commit()
        payload = content.to_dict()
        if token:
            payload["token"] = token
            payload["user"] = user.to_dict()
        return jsonify(payload)

    @app.get("/api/content")
    def list_content():
        user, _ = ensure_user(optional=True)
        if not user:
            return jsonify([])
        items = Content.query.filter_by(user_id=user.id).order_by(Content.id.desc()).all()
        return jsonify([item.to_dict() for item in items])

    @app.post("/api/quiz/generate")
    def create_quiz():
        verify_jwt_in_request(optional=True)
        payload = request.get_json(silent=True) or {}
        content_id = payload.get("content_id")
        question_types = payload.get("types") or ["mcq", "fill_blank", "true_false"]
        difficulty = payload.get("difficulty")
        try:
            num_questions = int(payload.get("num_questions") or 5)
        except (TypeError, ValueError):
            num_questions = 5
        if not content_id:
            return jsonify({"error": "Content not selected."}), 400
        if not question_types:
            return jsonify({"error": "Select at least one question type."}), 400

        user, _ = ensure_user(optional=True)
        content = None
        if user:
            content = Content.query.filter_by(id=content_id, user_id=user.id).first()
        if not content:
            return jsonify({"error": "Content not found."}), 404

        questions = generate_questions(
            content.body, question_types, difficulty, num_questions
        )
        if not questions:
            return (
                jsonify(
                    {"error": "Could not generate questions from this content."}
                ),
                400,
            )
        created = []
        for q in questions:
            question = Question(
                content_id=content.id,
                qtype=q["qtype"],
                question=q["question"],
                options_json=json.dumps(q.get("options") or []),
                answer=q["answer"],
                difficulty=q["difficulty"],
                source=q.get("source"),
            )
            db.session.add(question)
            created.append(question)
        db.session.commit()
        return jsonify([q.to_dict() for q in created])

    @app.get("/api/quiz/next")
    def next_question():
        user, _ = ensure_user(optional=True)
        if not user:
            return jsonify({"error": "No user available."}), 404
        performance = json.loads(user.performance_json or "{}")
        suggested = suggest_difficulty(performance, user.difficulty_pref)
        question = (
            Question.query.filter_by(difficulty=suggested)
            .order_by(Question.id.desc())
            .first()
        )
        if not question:
            question = Question.query.order_by(Question.id.desc()).first()
        if not question:
            return jsonify({"error": "No questions available."}), 404

        payload = question.to_dict()
        payload["suggested_difficulty"] = suggested
        return jsonify(payload)

    @app.post("/api/attempt")
    def log_attempt():
        user, _ = ensure_user(optional=True)
        if not user:
            return jsonify({"error": "No user available."}), 404
        payload = request.get_json(silent=True) or {}
        question_id = payload.get("question_id")
        is_correct = bool(payload.get("is_correct"))
        response_time_ms = int(payload.get("response_time_ms") or 0)
        question = Question.query.get(question_id)
        if not question:
            return jsonify({"error": "Question not found."}), 404

        attempt = Attempt(
            user_id=user.id,
            question_id=question.id,
            is_correct=is_correct,
            response_time_ms=response_time_ms,
            created_at=datetime.utcnow(),
        )
        db.session.add(attempt)

        performance = json.loads(user.performance_json or "{}")
        performance.setdefault("attempts", 0)
        performance.setdefault("correct", 0)
        performance["attempts"] += 1
        if is_correct:
            performance["correct"] += 1
        user.performance_json = json.dumps(performance)

        db.session.commit()
        return jsonify({"status": "ok", "performance": performance})

    @app.get("/api/admin/overview")
    def admin_overview():
        return jsonify(
            {
                "users": User.query.count(),
                "content_items": Content.query.count(),
                "questions": Question.query.count(),
                "attempts": Attempt.query.count(),
            }
        )

    @app.errorhandler(Exception)
    def handle_exception(err):
        return jsonify({"error": str(err)}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
