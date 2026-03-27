# Adaptive Quiz & Question Generator

This project follows the PDF specification and delivers a working adaptive quiz system with:

- User registration and login
- Content ingestion via pasted text
- Dynamic question generation (MCQ, fill‑in‑the‑blank, true/false)
- Adaptive difficulty selection based on performance
- Admin usage overview
- Polished UI/UX for the quiz experience

## Run locally

1. Open a PowerShell terminal in the project folder.
2. Install backend dependencies:

```powershell
cd backend
python -m pip install -r requirements.txt
```

3. Start the server:

```powershell
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

## Project structure

- `backend/app.py` — Flask API + server
- `backend/models.py` — SQLite models
- `backend/quiz_engine.py` — question generation + adaptive logic
- `backend/templates/index.html` — UI shell
- `backend/static/styles.css` — UI styling
- `backend/static/app.js` — UI logic
