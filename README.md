# Meraki

A production-style, full-stack multi-vendor marketplace where independent
sellers list and sell products to customers through one platform — built
as a software engineering portfolio project, not a CRUD demo.

## Status

🚧 In progress — built and documented stage by stage. See commit history
for the build order (architecture → schema → auth → ... → search → deploy).

## Stack

- **Frontend**: React, TypeScript, Vite, Tailwind CSS, React Router, Axios, TanStack Query
- **Backend**: FastAPI, SQLAlchemy 2.x, Pydantic, Alembic, PostgreSQL, JWT auth
- **Search**: PostgreSQL full-text + pgvector hybrid search
- **Deployment**: Vercel (frontend) · Render (backend) · Neon (PostgreSQL)

## Architecture

```
Client (React, Vercel)
   -> REST API (FastAPI, Render)
        -> Routers -> Services -> Repositories
   -> PostgreSQL (Neon, + pgvector)
```

Fuller docs, ER diagram, and engineering-decision notes live in `docs/`
as each stage lands.

## Running locally

See `backend/README.md` and `frontend/README.md` (added as each part comes online).

## License

Portfolio project — not for production use.
