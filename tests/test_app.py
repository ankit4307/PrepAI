import io
import json

from conftest import csrf
from services import ai, offline


# ---------- auth / security ----------
def test_post_without_csrf_is_rejected(client):
    r = client.post("/login", data={"email": "a@b.com", "password": "x"})
    assert r.status_code == 400


def test_register_validation_and_login(client):
    token = csrf(client)
    bad = client.post("/register", data={"csrf_token": token, "full_name": "A", "email": "nope",
                                         "graduation_year": "2026", "password": "password123",
                                         "confirm_password": "password123"})
    assert b"valid email" in bad.data
    short = client.post("/register", data={"csrf_token": token, "full_name": "A", "email": "a@b.com",
                                           "graduation_year": "2026", "password": "short",
                                           "confirm_password": "short"})
    assert b"at least 8" in short.data
    ok = client.post("/register", data={"csrf_token": token, "full_name": "A", "email": "a@b.com",
                                        "graduation_year": "2026", "password": "password123",
                                        "confirm_password": "password123"})
    assert b"Registration successful" in ok.data
    dup = client.post("/register", data={"csrf_token": token, "full_name": "A", "email": "A@b.com",
                                         "graduation_year": "2026", "password": "password123",
                                         "confirm_password": "password123"})
    assert b"already registered" in dup.data
    login = client.post("/login", data={"csrf_token": token, "email": "a@b.com", "password": "password123"})
    assert login.status_code == 302 and "/dashboard" in login.headers["Location"]


def test_login_throttling(client):
    token = csrf(client)
    for _ in range(5):
        client.post("/login", data={"csrf_token": token, "email": "x@y.com", "password": "wrong"})
    r = client.post("/login", data={"csrf_token": token, "email": "x@y.com", "password": "wrong"})
    assert r.status_code == 429


def test_protected_pages_redirect(client):
    for url in ("/dashboard", "/mock-interview", "/resume", "/analytics", "/history"):
        assert client.get(url).status_code == 302
    assert client.get("/api/analytics").status_code == 401


# ---------- pages render ----------
def test_all_pages_render(logged_in):
    client, _ = logged_in
    for url in ("/dashboard", "/mock-interview", "/resume", "/analytics", "/history",
                "/profile", "/technical", "/hr", "/"):
        r = client.get(url)
        assert r.status_code == 200, url
    assert client.get("/nope").status_code == 404


# ---------- interview flow (offline mode) ----------
def _run_interview(client, token, good=True):
    h = {"X-CSRF-Token": token}
    q = client.post("/api/generate-questions", json={"interview_type": "Technical", "difficulty": "Easy"}, headers=h)
    assert q.status_code == 200
    questions = q.get_json()["questions"]
    assert len(questions) == 5 and q.get_json()["personalized"] is False
    answer = ("Recursion is when a function calls itself. It needs a base case to stop. For example factorial "
              "uses a smaller sub-problem each call and the stack grows. Mutable lists, immutable tuples.")
    items = [{"question": x, "answer": answer if good else "no idea what it is"} for x in questions]
    e = client.post("/api/evaluate-all", json={"items": items}, headers=h)
    assert e.status_code == 200
    results = e.get_json()["results"]
    assert len(results) == 5 and all(r["source"] == "offline" for r in results)
    payload = [{"question": i["question"], "answer": i["answer"], "score": r["score"], "feedback": r, "time_sec": 30}
               for i, r in zip(items, results)]
    s = client.post("/api/save-session", json={"interview_type": "Technical", "difficulty": "Easy",
                                               "role": "Python Developer", "results": payload}, headers=h)
    assert s.status_code == 200
    return s.get_json(), results


def test_interview_flow_history_pdf_analytics(logged_in):
    client, token = logged_in
    saved, results = _run_interview(client, token)
    assert saved["average_score"] is not None

    page = client.get(f"/history?session={saved['session_id']}")
    assert page.status_code == 200 and b"Python Developer" in page.data

    pdf = client.get(f"/history/{saved['session_id']}/report.pdf")
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")

    data = client.get("/api/analytics").get_json()
    assert data["total"] == 1 and data["average"] == saved["average_score"]
    assert data["practice_minutes"] in (2, 3)  # 5 x 30s = 150s
    assert len(data["weak"]) == 5 and data["streak"] == 1


def test_user_cannot_see_other_users_session(logged_in, client):
    c, token = logged_in
    saved, _ = _run_interview(c, token)
    other = client.application.test_client()
    t2 = csrf(other)
    other.post("/register", data={"csrf_token": t2, "full_name": "B", "email": "b@b.com",
                                  "graduation_year": "2026", "password": "password123",
                                  "confirm_password": "password123"})
    other.post("/login", data={"csrf_token": t2, "email": "b@b.com", "password": "password123"})
    assert other.get(f"/history/{saved['session_id']}/report.pdf").status_code == 404
    assert b"Python Developer" not in other.get(f"/history?session={saved['session_id']}").data


def test_evaluate_input_validation(logged_in):
    client, token = logged_in
    h = {"X-CSRF-Token": token}
    assert client.post("/api/evaluate", json={"question": "q"}, headers=h).status_code == 400
    assert client.post("/api/evaluate", json={"question": "q", "answer": "x" * 3001}, headers=h).status_code == 400
    assert client.post("/api/evaluate-all", json={"items": "nope"}, headers=h).status_code == 400
    assert client.post("/api/generate-questions", json={"interview_type": "Bad"}, headers=h).status_code == 400
    assert client.post("/api/generate-questions", json={"difficulty": "Insane"}, headers=h).status_code == 400
    assert client.post("/api/save-session", json={"results": ["junk"]}, headers=h).status_code == 400


# ---------- evaluators ----------
def test_offline_evaluator_rewards_good_answers():
    q = "What is recursion? Give a simple example."
    good = ("Recursion is when a function calls itself on a smaller sub-problem until it reaches a base case. "
            "For example factorial of n is n times factorial of n-1. Each call uses the call stack.")
    bad = "it is a thing in programming"
    assert offline.heuristic_evaluate(q, good)["score"] >= 7
    assert offline.heuristic_evaluate(q, bad)["score"] <= 3


def test_score_guard_caps_short_answers(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    fake = lambda prompt: json.dumps({"score": 10, "strengths": ["a"], "improvements": ["b"], "sample_answer": "c"})
    r = ai.evaluate_answer("What is OOP?", "idk", ask=fake)
    assert r["source"] == "ai" and r["score"] <= 1


def test_ai_failure_falls_back_to_offline(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")

    def boom(prompt):
        raise RuntimeError("quota")
    r = ai.evaluate_answer("What is recursion? Give a simple example.",
                           "A function calling itself with a base case, for example factorial.", ask=boom)
    assert r["source"] == "offline"


def test_ai_json_in_code_fence_is_parsed():
    assert ai.parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_filler_counter():
    assert offline.count_fillers("Um, basically I think, you know, it is actually fine") == 4


# ---------- resume ----------
RESUME = """
Rahul Sharma | rahul@example.com | +91 9876543210 | github.com/rahul | linkedin.com/in/rahul
Education: B.Tech Computer Science, ABC College, CGPA 8.2
Skills: Python, Flask, SQL, Git, REST API, OOP, Pandas, NumPy
Projects: Developed a placement portal using Flask and SQL, reducing manual work by 40%.
Built a REST API with 12 endpoints and implemented testing with pytest. Deployed on a cloud server.
Internship: Software intern at XYZ, designed a dashboard used by 200 students and improved load time by 30%.
Certifications: Python for Everybody. Achievements: Won college hackathon 2025.
""" * 2


def test_resume_text_analysis_saved(logged_in):
    client, token = logged_in
    r = client.post("/api/resume/analyze", data={"role": "Python Developer", "text": RESUME},
                    headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    d = r.get_json()
    assert 50 <= d["ats_score"] <= 100 and "python" in d["matched_keywords"]
    assert d["sections"]["Education"] is True
    assert client.get("/resume").status_code == 200
    assert client.get("/api/analytics").get_json()["resume"][0]["score"] == d["ats_score"]


def test_resume_validation_and_pdf_upload(logged_in):
    client, token = logged_in
    h = {"X-CSRF-Token": token}
    assert client.post("/api/resume/analyze", data={"text": "too short"}, headers=h).status_code == 400
    bad = client.post("/api/resume/analyze", headers=h,
                      data={"file": (io.BytesIO(b"MZ"), "virus.exe")}, content_type="multipart/form-data")
    assert bad.status_code == 400
    # a real (generated) PDF containing the resume text
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in RESUME.strip().splitlines()[:9]:
        c.drawString(40, y, line[:110]); y -= 18
    c.save()
    buf.seek(0)
    ok = client.post("/api/resume/analyze", headers=h, content_type="multipart/form-data",
                     data={"role": "Python Developer", "file": (buf, "cv.pdf")})
    assert ok.status_code == 200, ok.data
    assert ok.get_json()["ats_score"] > 30


def test_resume_upload_size_limit(logged_in):
    client, token = logged_in
    big = io.BytesIO(b"a" * (3 * 1024 * 1024))
    r = client.post("/api/resume/analyze", headers={"X-CSRF-Token": token}, content_type="multipart/form-data",
                    data={"file": (big, "cv.txt")})
    assert r.status_code == 413
