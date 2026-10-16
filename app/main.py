"""Students Database CRUD API (FastAPI + SQLite) with optional Ollama AI."""
import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status

from . import ai, crud, database
from .schemas import (
    AIAnswer, AIQuestion, Student, StudentCreate, StudentUpdate,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(
    title="Students Database API",
    description="CRUD API for student records. Bonus: /ai/ask answers "
                "questions using a local Ollama model grounded in DB records.",
    version="1.0.0",
    lifespan=lifespan,
)


def get_db():
    conn = database.get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _not_found(student_id: int) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND,
                         f"Student with id {student_id} not found")


@app.get("/", tags=["Health"])
def root():
    return {"message": "Students API is running", "docs": "/docs"}


# ---------- CREATE ----------
@app.post("/students", response_model=Student,
          status_code=status.HTTP_201_CREATED, tags=["Students"])
def create_student(payload: StudentCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        return crud.create_student(db, payload.model_dump(mode="json"))
    except crud.DuplicateEmailError:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "A student with this email already exists")


# ---------- READ (list + filter) ----------
@app.get("/students", response_model=list[Student], tags=["Students"])
def list_students(
    name: Optional[str] = Query(None, description="Partial name match"),
    course: Optional[str] = Query(None, description="Partial course match"),
    email: Optional[str] = Query(None, description="Exact email match"),
    born_after: Optional[date] = Query(None, description="DOB on/after (YYYY-MM-DD)"),
    born_before: Optional[date] = Query(None, description="DOB on/before (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: sqlite3.Connection = Depends(get_db),
):
    return crud.list_students(
        db, name=name, course=course, email=email,
        dob_from=born_after.isoformat() if born_after else None,
        dob_to=born_before.isoformat() if born_before else None,
        skip=skip, limit=limit,
    )


# ---------- READ (single) ----------
@app.get("/students/{student_id}", response_model=Student, tags=["Students"])
def get_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    student = crud.get_student(db, student_id)
    if student is None:
        raise _not_found(student_id)
    return student


def _apply_update(db, student_id: int, changes: dict):
    try:
        student = crud.update_student(db, student_id, changes)
    except crud.DuplicateEmailError:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "A student with this email already exists")
    except crud.MissingContactError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if student is None:
        raise _not_found(student_id)
    return student


# ---------- UPDATE (full) ----------
@app.put("/students/{student_id}", response_model=Student, tags=["Students"])
def replace_student(student_id: int, payload: StudentCreate,
                    db: sqlite3.Connection = Depends(get_db)):
    return _apply_update(db, student_id, payload.model_dump(mode="json"))


# ---------- UPDATE (partial) ----------
@app.patch("/students/{student_id}", response_model=Student, tags=["Students"])
def update_student(student_id: int, payload: StudentUpdate,
                   db: sqlite3.Connection = Depends(get_db)):
    changes = payload.model_dump(mode="json", exclude_unset=True)
    return _apply_update(db, student_id, changes)


# ---------- DELETE ----------
@app.delete("/students/{student_id}", tags=["Students"])
def delete_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    if not crud.delete_student(db, student_id):
        raise _not_found(student_id)
    return {"message": f"Student {student_id} deleted successfully"}


# ---------- OPTIONAL BONUS: local AI ----------
@app.post("/ai/ask", response_model=AIAnswer, tags=["AI (optional)"])
def ask_ai(payload: AIQuestion, db: sqlite3.Connection = Depends(get_db)):
    return ai.answer_question(db, payload.question)
