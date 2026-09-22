# Backend — Marketplace API

FastAPI + SQLAlchemy 2.x + PostgreSQL.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env          # then edit DATABASE_URL etc.
uvicorn app.main:app --reload
```

API docs (Swagger UI) will be at http://localhost:8000/docs

## Tests

```bash
pytest -v
```

## Layout

```
app/
  main.py          FastAPI app + middleware + router registration
  config.py        Settings loaded from environment variables
  database.py      Engine, session factory, declarative Base
  models/          SQLAlchemy ORM models
  schemas/         Pydantic request/response models
  routers/         HTTP layer — thin, delegates to services
  services/        Business logic
  repositories/    Data access (no business rules)
  dependencies/     FastAPI dependencies (auth, db session, etc.)
  utils/           Pure helper functions (hashing, JWT)
```
