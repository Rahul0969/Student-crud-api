"""Optional Ollama extension.

Safety design: the model NEVER writes or runs SQL. Backend code parses the
question into a small set of whitelisted filters, runs parameterised queries,
and gives the retrieved rows to the model as context. If Ollama is not
running, a deterministic answer built from the same records is returned.
"""
import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from typing import Optional

from . import crud

MAX_CONTEXT_RECORDS = 50
COUNT_RE = r"how many|count|number of"


def _ollama_url() -> str:
    return os.getenv("OLLAMA_URL", "http://localhost:11434")


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.2:1b")


# ---------- 1. understand the question (whitelisted filters only) ----------
def parse_question(question: str, courses: list[str], names: list[str]) -> dict:
    q = question.lower()
    filters: dict = {}

    m = re.search(r"born\s+in\s+(\d{4})", q)
    if m:
        y = int(m.group(1))
        filters["dob_from"], filters["dob_to"] = f"{y}-01-01", f"{y}-12-31"
    else:
        m = re.search(r"after\s+(\d{4})", q)
        if m:
            filters["dob_from"] = f"{int(m.group(1)) + 1}-01-01"
        m = re.search(r"before\s+(\d{4})", q)
        if m:
            filters["dob_to"] = f"{int(m.group(1)) - 1}-12-31"

    for course in courses:
        if course.lower() in q:
            filters["course"] = course
            break

    for full in names:
        first = full.split()[0].lower()
        if full.lower() in q or re.search(rf"\b{re.escape(first)}\b", q):
            filters["name"] = full
            break

    filters["is_count"] = bool(re.search(COUNT_RE, q))
    return filters


# ---------- 2. retrieve records ----------
def retrieve(db: sqlite3.Connection, question: str) -> tuple[int, int, list[dict]]:
    """Returns (total_in_db, total_matching, records_for_context)."""
    courses = crud.distinct_courses(db)
    names = [s["name"] for s in crud.list_students(db, limit=None)]
    f = parse_question(question, courses, names)
    db_filters = {k: f[k] for k in ("name", "course", "dob_from", "dob_to") if k in f}

    total = crud.count_students(db)
    matching = crud.count_students(db, **db_filters)
    records = crud.list_students(db, limit=MAX_CONTEXT_RECORDS, **db_filters)
    return total, matching, records


# ---------- 3. build prompt ----------
def _fmt(s: dict) -> str:
    return (f"- ID {s['id']}: {s['name']}, born {s['date_of_birth']}, "
            f"course: {s['course'] or 'N/A'}, enrolled: {s['enrollment_date'] or 'N/A'}")


def build_prompt(question: str, total: int, matching: int, records: list[dict]) -> str:
    lines = "\n".join(_fmt(r) for r in records) or "(no matching records)"
    return (
        "You are an assistant for a student database. Answer ONLY using the "
        "data below. If the data does not contain the answer, say you do not "
        "know. Be brief and accurate.\n\n"
        f"Total students in database: {total}\n"
        f"Students matching the question: {matching}\n"
        f"Matching records:\n{lines}\n\n"
        f"Question: {question}\nAnswer:"
    )


# ---------- 4. fallback answer (no LLM) ----------
def fallback_answer(question: str, total: int, matching: int, records: list[dict]) -> str:
    if re.search(COUNT_RE, question.lower()):
        return f"There are {matching} matching student(s) (total in database: {total})."
    if not records:
        return "No students match your question."
    names = "; ".join(f"{r['name']} (born {r['date_of_birth']})" for r in records)
    return f"{matching} matching student(s): {names}"


# ---------- 5. call Ollama ----------
def ask_ollama(prompt: str) -> Optional[str]:
    body = json.dumps({
        "model": _ollama_model(),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0},
    }).encode()
    req = urllib.request.Request(
        f"{_ollama_url()}/api/chat", data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        return data.get("message", {}).get("content", "").strip() or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def answer_question(db: sqlite3.Connection, question: str) -> dict:
    total, matching, records = retrieve(db, question)
    text = ask_ollama(build_prompt(question, total, matching, records))
    if text:
        return {"question": question, "answer": text,
                "records_used": len(records), "source": "ollama",
                "model": _ollama_model()}
    return {"question": question,
            "answer": fallback_answer(question, total, matching, records),
            "records_used": len(records), "source": "fallback", "model": None}
