"""SQLite connection helpers (standard-library sqlite3, no ORM needed)."""
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    date_of_birth   TEXT NOT NULL,          -- ISO date: YYYY-MM-DD
    email           TEXT UNIQUE,
    phone           TEXT,
    course          TEXT,
    address         TEXT,
    enrollment_date TEXT,                   -- ISO date: YYYY-MM-DD
    CHECK (email IS NOT NULL OR phone IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_students_course ON students(course);
CREATE INDEX IF NOT EXISTS idx_students_dob ON students(date_of_birth);
"""


def get_db_path() -> str:
    # Read at call time so tests can point to a temporary file.
    return os.getenv("STUDENTS_DB_PATH", "students.db")


def get_connection() -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may run a dependency and the route in
    # different worker threads; each request still gets its own connection.
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
