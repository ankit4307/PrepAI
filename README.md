# PrepAI – AI Interview & Smart Placement Preparation System

Flask + SQLite + Google Gemini. Students register, build a profile, take **personalised AI mock interviews**,
get **feedback on every answer**, analyse their **resume (ATS score)** and track progress with **analytics**.

## Features
| Module | What it does |
|---|---|
| Auth & security | Hashed passwords, CSRF tokens, login throttling, secure cookies, per-user AI rate limit |
| Profile | Skills, projects, target role → used to personalise questions |
| AI Mock Interview | Technical / HR / Mixed, Easy / Medium / Hard, 5 questions from Gemini, never repeats recent questions |
| Answer evaluation | Score /10, strengths, improvements, sample answer; filler-word counter; per-question timer |
| Voice answers | Speak instead of typing (browser Web Speech API, Chrome/Edge) |
| **Offline mode** | No API key / quota over / no internet → rule-based evaluator + question bank. App never breaks in a demo |
| Resume ATS Analyzer | Upload PDF/TXT or paste text → ATS score, keyword gap, section checklist, fixes (AI or rule-based) |
| Analytics | Score trend, average by type, weakest answers, streak, practice minutes (Chart.js) |
| History + PDF report | Every interview is saved; download a PDF report |

## Run locally
```bash
python -m venv venv
venv\Scripts\activate            # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # optional: add GEMINI_API_KEY (get one free at aistudio.google.com)
python app.py
```
Open http://127.0.0.1:5000. Without `GEMINI_API_KEY` the app runs in **offline mode**.

## Run the tests
```bash
pip install pytest
python -m pytest -q          # 16 tests: auth, CSRF, interview flow, PDF, analytics, resume, evaluators
```

## Project structure
```
app.py                  Flask routes (auth, interview, resume, analytics, history, PDF)
database.py             SQLite schema + auto-migrations
services/ai.py          Gemini calls, JSON parsing, score guard, AI → offline fallback
services/offline.py     Rule-based answer evaluator + resume (ATS) heuristic + keyword banks
services/report.py      PDF report (reportlab)
templates/              base.html + pages (Bootstrap 5, Chart.js)
tests/                  pytest suite (runs without internet / API key)
docs/                   Project report (Word) + viva questions
```

## Database (SQLite)
`users` 1—1 `student_profiles`; `users` 1—N `interview_sessions` 1—N `interview_answers`; `users` 1—N `resume_analyses`.

## How the AI + offline fallback works
1. `evaluate_answer()` asks Gemini for JSON (score, strengths, improvements, sample answer).
2. A **score guard** caps very short answers so the AI cannot inflate scores.
3. If Gemini fails/timeouts/no key → `heuristic_evaluate()` scores by key-concept coverage, length, example and structure.
4. Each result carries `source: "ai" | "offline"`, shown in the UI.

## Security notes
Secrets only in `.env` (never commit it). CSRF on every POST, input validation, parameterised SQL,
AI output rendered with `textContent` (no XSS), 2 MB upload cap on resume route, 64 KB elsewhere, users can only open their own sessions.

## Deployment
`gunicorn app:app` (set `SECRET_KEY` and `GEMINI_API_KEY` as environment variables). For many users switch SQLite → PostgreSQL.
