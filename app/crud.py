"""Database operations. Every query is parameterised (no SQL injection)."""
import sqlite3
from typing import Any, Optional

FIELDS = [
    "name", "date_of_birth", "email", "phone",
    "course", "address", "enrollment_date",
]


class DuplicateEmailError(Exception):
    pass


class MissingContactError(ValueError):
    pass


def _row(row: Optional[sqlite3.Row]) -> Optional[dict]:
    return dict(row) if row else None


def _clean(data: dict) -> dict:
    out = dict(data)
    if out.get("email"):
        out["email"] = out["email"].strip().lower()
    return out


def create_student(db: sqlite3.Connection, data: dict) -> dict:
    data = _clean(data)
    values = [data.get(f) for f in FIELDS]
    try:
        cur = db.execute(
            f"INSERT INTO students ({', '.join(FIELDS)}) "
            f"VALUES ({', '.join('?' * len(FIELDS))})",
            values,
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.rollback()
        if "email" in str(exc).lower():
            raise DuplicateEmailError(data.get("email"))
        raise MissingContactError("Provide at least an email or a phone number.")
    return get_student(db, cur.lastrowid)


def get_student(db: sqlite3.Connection, student_id: int) -> Optional[dict]:
    cur = db.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    return _row(cur.fetchone())


def _filters(name, course, email, dob_from, dob_to):
    clauses: list[str] = []
    params: list[Any] = []
    if name:
        clauses.append("name LIKE ?")
        params.append(f"%{name}%")
    if course:
        clauses.append("course LIKE ?")
        params.append(f"%{course}%")
    if email:
        clauses.append("email = ?")
        params.append(email.strip().lower())
    if dob_from:
        clauses.append("date_of_birth >= ?")
        params.append(dob_from)
    if dob_to:
        clauses.append("date_of_birth <= ?")
        params.append(dob_to)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def list_students(
    db: sqlite3.Connection,
    name: Optional[str] = None,
    course: Optional[str] = None,
    email: Optional[str] = None,
    dob_from: Optional[str] = None,
    dob_to: Optional[str] = None,
    skip: int = 0,
    limit: Optional[int] = 100,
) -> list[dict]:
    where, params = _filters(name, course, email, dob_from, dob_to)
    sql = f"SELECT * FROM students {where} ORDER BY id"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params += [limit, skip]
    return [dict(r) for r in db.execute(sql, params).fetchall()]


def count_students(
    db: sqlite3.Connection,
    name: Optional[str] = None,
    course: Optional[str] = None,
    email: Optional[str] = None,
    dob_from: Optional[str] = None,
    dob_to: Optional[str] = None,
) -> int:
    where, params = _filters(name, course, email, dob_from, dob_to)
    return db.execute(f"SELECT COUNT(*) FROM students {where}", params).fetchone()[0]


def update_student(
    db: sqlite3.Connection, student_id: int, changes: dict
) -> Optional[dict]:
    """Apply changes (full or partial). Returns None if the student is missing."""
    current = get_student(db, student_id)
    if current is None:
        return None
    merged = _clean({**current, **changes})
    if not merged.get("email") and not merged.get("phone"):
        raise MissingContactError("Provide at least an email or a phone number.")
    try:
        db.execute(
            f"UPDATE students SET {', '.join(f + ' = ?' for f in FIELDS)} WHERE id = ?",
            [merged.get(f) for f in FIELDS] + [student_id],
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise DuplicateEmailError(merged.get("email"))
    return get_student(db, student_id)


def delete_student(db: sqlite3.Connection, student_id: int) -> bool:
    cur = db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    return cur.rowcount > 0


def distinct_courses(db: sqlite3.Connection) -> list[str]:
    rows = db.execute(
        "SELECT DISTINCT course FROM students WHERE course IS NOT NULL"
    ).fetchall()
    return [r[0] for r in rows]
