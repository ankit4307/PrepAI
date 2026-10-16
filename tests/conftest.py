import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# use a throw-away database and NO api key (offline mode) for all tests
_tmp = tempfile.mkdtemp()
os.environ["PREPAI_DB"] = os.path.join(_tmp, "test.db")
os.environ.pop("GEMINI_API_KEY", None)
os.environ["SECRET_KEY"] = "test-secret"

import app as app_module  # noqa: E402
from database import init_db  # noqa: E402


@pytest.fixture()
def client():
    path = os.environ["PREPAI_DB"]
    if os.path.exists(path):
        os.remove(path)
    init_db()
    app_module._failed_logins.clear()
    app_module._calls.clear()
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def csrf(client):
    """Visit a page so a CSRF token exists in the session and return it."""
    client.get("/login")
    with client.session_transaction() as s:
        return s["csrf_token"]


@pytest.fixture()
def logged_in(client):
    token = csrf(client)
    client.post("/register", data={
        "csrf_token": token, "full_name": "Test Student", "email": "t@example.com",
        "college": "ABC", "course": "B.Tech", "graduation_year": "2026",
        "password": "password123", "confirm_password": "password123"})
    client.post("/login", data={"csrf_token": token, "email": "t@example.com", "password": "password123"})
    token = csrf(client)
    return client, token
