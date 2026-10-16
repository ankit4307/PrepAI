"""SQLite helpers + schema (with tiny auto-migrations so old database.db files keep working)."""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def db_path():
    # PREPAI_DB lets the tests use a temporary database
    return os.getenv("PREPAI_DB") or os.path.join(BASE_DIR, "database.db")


def get_db_connection():
    connection = sqlite3.connect(db_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _add_column_if_missing(connection, table, column, definition):
    cols = [row["name"] for row in connection.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            college TEXT,
            course TEXT,
            graduation_year INTEGER,
            password TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS student_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            skills TEXT,
            projects TEXT,
            certifications TEXT,
            target_role TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            interview_type TEXT NOT NULL,
            role TEXT,
            average_score REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS interview_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            score INTEGER,
            feedback TEXT,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id)
                ON DELETE CASCADE
        )
    """)

    # NEW: resume analyses (ATS score history)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS resume_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            target_role TEXT,
            ats_score INTEGER,
            source TEXT,
            result TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # migrations for databases created by the older version
    _add_column_if_missing(connection, "interview_sessions", "difficulty", "TEXT")
    _add_column_if_missing(connection, "interview_sessions", "total_time_sec", "INTEGER")
    _add_column_if_missing(connection, "interview_answers", "time_sec", "INTEGER")

    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_user ON interview_sessions(user_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_answers_session ON interview_answers(session_id)"
    )
    connection.commit()
    connection.close()
