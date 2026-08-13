# ATS Resume Screening System — Project Setup

Project scaffold only. No business logic, no AI matching, no auth logic yet —
this document covers environment setup and running the empty app.

## 1. Prerequisites

- Python 3.11+
- MySQL 8.x running locally (or accessible via `DATABASE_URL`)
- Redis (for Celery, used later)
- `git`

## 2. Create and activate a virtual environment

```bash
# from the project root
python3 -m venv venv

# activate it
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

## 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> Note: `torch` and `transformers` are sizeable downloads (used by the AI layer
> in a later phase). Installing them now ensures the environment is ready.

## 4. Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env` and set at minimum:
- `SECRET_KEY` — any long random string
- `DB_USER`, `DB_PASSWORD`, `DB_NAME` — matching your local MySQL setup
- `DATABASE_URL` — should match the DB_* values above

## 5. Create the MySQL database

```sql
CREATE DATABASE ats_resume_db CHARACTER SET utf8mb4;
```

(Table creation/migrations come in a later step via Alembic — no models exist yet.)

## 6. Run the application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then visit:
- `http://localhost:8000/health` — health check endpoint
- `http://localhost:8000/docs` — auto-generated Swagger UI (all endpoint
  routers are mounted but currently empty)

## 7. Project structure

See `ATS_Resume_Screening_System_Design.md` (architecture doc) for the full
folder structure, responsibilities, and rationale. Quick map:

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI entrypoint |
| `app/core/` | Settings + logging configuration |
| `app/api/v1/` | Route definitions (currently empty routers) |
| `app/models/` | SQLAlchemy models (not yet created) |
| `app/schemas/` | Pydantic request/response schemas (not yet created) |
| `app/services/` | Business logic (not yet created) |
| `app/ai/` | Hugging Face model wrappers (not yet created) |
| `app/db/` | DB engine/session setup |
| `static/` | CSS, JS, uploaded resumes |
| `templates/` | Server-rendered HTML (Jinja2) |
| `logs/` | Rotating log files (`app.log`) |
| `alembic/` | Database migrations |

## 8. What's intentionally NOT built yet

- No database models or migrations content
- No authentication logic (JWT scaffolding exists, no login/register logic)
- No resume parsing or AI matching logic
- No frontend pages beyond a placeholder landing page

These are built in the next phase, on top of this scaffold.
