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

### Option A — run MySQL via Docker (recommended)

```bash
cd docker
docker compose up --build
```

This brings up a real MySQL 8 container and the FastAPI app together —
the app waits for MySQL to report healthy before starting. The app will
be available at `http://localhost:8000`.

### Option B — run against a local MySQL install

If you're running MySQL yourself (not via Docker), create the database
and a dedicated user:

```sql
CREATE DATABASE ats_resume_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ats_user'@'localhost' IDENTIFIED BY 'change_this_password';
GRANT ALL PRIVILEGES ON ats_resume_db.* TO 'ats_user'@'localhost';
FLUSH PRIVILEGES;
```

Then apply the schema via Alembic rather than `Base.metadata.create_all`
(migrations are the source of truth for schema changes from here on):

```bash
alembic upgrade head
```

## 6. Run the application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then visit:
- `http://localhost:8000/health` — health check endpoint
- `http://localhost:8000/docs` — Swagger UI

## 7. Run the test suite

```bash
pip install -r requirements.txt  # includes pytest, pytest-cov, httpx
pytest
```

The suite uses an in-memory SQLite database per test (fast, no external
dependencies) with `sentence_transformers` stubbed out — see
`tests/conftest.py` for why. This means the suite does **not** by itself
catch MySQL-specific issues (collation quirks, foreign-key/InnoDB
behavior). Those are covered separately: every model and migration in
this project has been manually verified against a real MySQL 8 instance,
including a full `alembic upgrade → downgrade → upgrade` cycle and a
cascade-delete test. If you change the schema, re-verify against real
MySQL before trusting the change, not just the SQLite-backed test suite.

## 8. Database migrations (Alembic)

The initial schema migration lives in `alembic/versions/`. After
changing any model in `app/models/models.py`, generate a new migration:

```bash
alembic revision --autogenerate -m "Describe your change"
```

**Always review the generated file before applying it** — Alembic's
autogenerate is a starting point, not guaranteed-correct output. In
particular, watch for `downgrade()` functions that call `op.drop_index()`
on a foreign-key-backing column before `op.drop_table()`: MySQL/InnoDB
refuses to drop such an index independently of its constraint
(`Cannot drop index '...': needed in a foreign key constraint`). The fix
is to remove those explicit index drops — `op.drop_table()` already
removes a table's indexes and FK constraints together. This exact issue
was hit and fixed in the initial migration; it will recur on any new
foreign-key column unless watched for.

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
