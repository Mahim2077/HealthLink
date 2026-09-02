# HealthLink

HealthLink is a modular healthcare information platform with separate Citizen,
Professional, and Admin portal contexts. This repository implements the
documented roadmap sequentially through Phase 14 and intentionally stops before
Phase 15.

## Applications

- `backend/` — FastAPI, SQLAlchemy, Alembic, and PostgreSQL
- `frontend/` — Next.js App Router, TypeScript, and Tailwind CSS
- `docs/` — implementation decisions, assumptions, and phase verification

The three Markdown files at the repository root are the governing project
documents and are preserved under their attached filenames.

## Local prerequisites

- Python 3.13+
- Node.js 24.15+
- PostgreSQL 17+ (or a Neon PostgreSQL connection)

## Backend quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
# Set DATABASE_URL and a 32+ character JWT_SECRET_KEY in backend/.env.
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API health check is available at `http://localhost:8000/health`.

## Frontend quick start

```powershell
Set-Location frontend
npm.cmd install
Copy-Item .env.example .env.local
npm.cmd run dev
```

The web application is available at `http://localhost:3000`.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
Set-Location frontend
npm.cmd run lint
npm.cmd run test
npm.cmd run build
```

See [implementation progress](docs/implementation-progress.md) for phase-by-phase
status and verification evidence.

For production CI/CD and Vercel setup, see the
[GitHub Actions and Vercel deployment guide](docs/VERCEL_GITHUB_ACTIONS_DEPLOYMENT.md).
