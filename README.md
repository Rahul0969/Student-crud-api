# Students Database CRUD API

Python backend for managing student records (Create, Read, Update, Delete) using **FastAPI** and **SQLite**.
Bonus: a local **Ollama** AI endpoint that answers natural-language questions grounded in the stored records.

## Features
- Full CRUD with input validation (email format, phone pattern, no future DOB, email or phone required)
- Unique student ID (auto-increment) and unique email (duplicate returns 409)
- Filtering and pagination: `name`, `course`, `email`, `born_after`, `born_before`, `skip`, `limit`
- Proper errors: 404 for missing records, 409 for duplicates, 422 for invalid input
- Optional AI endpoint `POST /ai/ask` (the model never runs SQL)
- Automated tests with pytest

## Project structure
```
students-crud-api/
├── app/
│   ├── main.py       # FastAPI routes
│   ├── crud.py       # SQLite operations (parameterised queries)
│   ├── database.py   # connection + table schema
│   ├── schemas.py    # Pydantic validation models
│   └── ai.py         # optional Ollama extension
├── tests/test_api.py
├── seed.py           # loads dummy data
├── requirements.txt
└── .env.example
```

## Prerequisites
- Python 3.10+
- (Optional, for AI bonus) [Ollama](https://ollama.com) installed

## Installation
```bash
git clone <your-repo-url>
cd students-crud-api
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
python seed.py                   # optional: load 8 dummy students
uvicorn app.main:app --reload
```
- API: http://127.0.0.1:8000
- Interactive docs (Swagger): http://127.0.0.1:8000/docs

The SQLite file `students.db` is created automatically and data persists between restarts.

## API endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/students` | Create a student |
| GET | `/students` | List / filter students |
| GET | `/students/{id}` | View a student |
| PUT | `/students/{id}` | Replace all details |
| PATCH | `/students/{id}` | Update some details |
| DELETE | `/students/{id}` | Delete a student |
| POST | `/ai/ask` | (Optional) Ask AI about the data |

### Sample requests (curl)
```bash
# Create
curl -X POST http://127.0.0.1:8000/students -H "Content-Type: application/json" \
  -d '{"name":"Aarav Sharma","date_of_birth":"2004-05-17","email":"aarav@example.com","phone":"+91 98765 43210","course":"Computer Science","enrollment_date":"2022-08-01"}'

# List all / filter
curl http://127.0.0.1:8000/students
curl "http://127.0.0.1:8000/students?course=Data&born_after=2005-01-01"

# View one
curl http://127.0.0.1:8000/students/1

# Partial update
curl -X PATCH http://127.0.0.1:8000/students/1 -H "Content-Type: application/json" -d '{"course":"AI & ML"}'

# Delete
curl -X DELETE http://127.0.0.1:8000/students/1
```

## Optional: AI with Ollama
```bash
ollama pull llama3.2:1b
ollama serve                      # usually already running
curl -X POST http://127.0.0.1:8000/ai/ask -H "Content-Type: application/json" \
  -d '{"question":"List students born after 2005"}'
```
How it works: backend code turns the question into whitelisted filters (born after/before/in a year, course, name, count),
runs parameterised queries, and passes the matching records to the model as context.
**The model never generates or executes SQL.** If Ollama is not running, the endpoint returns a
direct answer built from the same records (`"source": "fallback"`).

Config via environment variables (see `.env.example`): `OLLAMA_URL`, `OLLAMA_MODEL`, `STUDENTS_DB_PATH`.

## Run tests
```bash
pytest -v
```

## Security notes
- Only dummy data is used; no secrets or real personal information are committed (`.env` and `*.db` are git-ignored).
- All SQL uses parameter binding.
