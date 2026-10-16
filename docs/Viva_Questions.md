# Viva preparation – PrepAI

1. **Why Flask?** Lightweight, easy to structure routes/templates, ideal for a small web app with REST-style JSON APIs.
2. **Why SQLite?** Zero configuration, file-based, enough for a college-scale project. Can migrate to PostgreSQL (SQL is standard).
3. **How do you protect passwords?** `werkzeug.security.generate_password_hash` (salted PBKDF2/scrypt hash); plain passwords are never stored.
4. **What is CSRF and how did you stop it?** Attacker site making a logged-in user's browser send a request. Every POST must carry a random per-session token (`X-CSRF-Token` / hidden field), compared with `secrets.compare_digest`.
5. **How do you prevent SQL injection?** Only parameterised queries (`?` placeholders).
6. **How do you prevent XSS from AI output?** Jinja autoescaping and `textContent` in JavaScript – never `innerHTML`.
7. **What if the Gemini API is down or the key is missing?** Offline mode: rule-based evaluator + built-in question bank, so the system always responds.
8. **How is an answer scored?** Gemini is given a strict rubric (0–10). A score guard caps very short answers. Offline: key-concept coverage (60%), length, example, structure.
9. **How does the ATS analyzer work?** Extracts text (pypdf), checks sections (education, skills, projects...), contact links, action verbs, numbers, resume length and keyword match for the target role; AI adds role-specific advice.
10. **How do you handle slow AI responses?** Background thread pool, 10 s timeout for questions, evaluations run in parallel with a 40 s overall deadline, then fallback.
11. **What is rate limiting here?** In-memory sliding window: 40 AI calls / 10 min / user, and 5 failed logins / 10 min.
12. **How would you scale it?** PostgreSQL, Redis for rate-limit/cache, Celery for background AI jobs, gunicorn behind nginx.
13. **Future scope?** Coding round with code execution, video/emotion analysis, company-specific question sets, admin panel, mobile app.
14. **What testing did you do?** 16 automated pytest tests (auth, CSRF, access control, interview flow, PDF, analytics, resume upload limits, evaluators) plus manual browser testing.
