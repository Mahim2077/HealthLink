# HealthLink development setup on a new PC

This guide sets up a Windows development workstation while keeping local work
isolated from HealthLink production.

## 1. Install prerequisites

Install:

- Git
- Python 3.13 or newer
- Node.js 24.15 or newer within the Node 24 release line; do not use Node 25
- PostgreSQL 17 or newer
- A code editor such as Visual Studio Code
- Optional: Vercel CLI for deployment inspection

Verify the installed tools in PowerShell:

```powershell
git --version
python --version
node --version
npm --version
psql --version
```

## 2. Clone the repository

```powershell
git clone https://github.com/Mahim2077/HealthLink.git
Set-Location HealthLink
git switch main
git pull --ff-only origin main
git status
git log -2 --oneline
```

At the time this guide was created, the expected latest commits were:

```text
ba5f3e8 docs(release): record production verification [skip ci]
c8d2f26 feat(platform): modernize discovery and clinical workflows
```

Read these files before editing:

1. `AGENTIC_IMPLEMENTATION_HANDOFF_CURRENT.md`
2. `frontend/AGENTS.md`
3. `docs/implementation-progress.md`
4. `docs/implementation-assumptions.md`

The current workspace contains locally implemented Phases 22–27 awaiting review
and release. These uncommitted changes are not yet in a fresh GitHub clone; move
them separately or wait for an authorized release. The next development phase is
Phase 28. The released database head remains `0030_doctor_locations`.

## 3. Create a development branch

Avoid developing directly on `main`:

```powershell
git switch -c feature/phase-28
```

If Codex will primarily manage the branch, use:

```powershell
git switch -c codex/phase-28
```

Replace `phase-28` with a short description when working on a different task.

## 4. Create local PostgreSQL databases

Use separate development and test databases. Do not use the production
Supabase connection for routine development or testing.

Open PostgreSQL:

```powershell
psql -U postgres
```

Create isolated local resources:

```sql
CREATE USER healthlink_dev WITH PASSWORD 'choose-a-local-password';
CREATE DATABASE healthlink_dev OWNER healthlink_dev;
CREATE DATABASE healthlink_test OWNER healthlink_dev;
\q
```

These databases must not contain production patient data.

## 5. Configure the backend

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env`. At minimum, configure:

```dotenv
APP_ENV=development
DEBUG=true
DATABASE_URL=postgresql+psycopg://healthlink_dev:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/healthlink_dev
JWT_SECRET_KEY=YOUR_RANDOM_SECRET_OF_AT_LEAST_32_CHARACTERS
FRONTEND_URL=http://localhost:3000
```

Leave `AI_API_KEY` empty and keep `AI_ENABLED=false` plus
`AI_RECORD_CONTEXT_ENABLED=false` unless an approved AI environment specifically
requires real provider calls. Never expose the key through a `NEXT_PUBLIC_`
variable. The scheduled reminder workflow has been removed, so a cron secret is
not needed for normal development.

Never commit `backend\.env`.

The local Phase-22–27 AI implementation now supports GroqCloud, mock and Gemini.
Groq/Qwen 3.8 is the selected (disabled) default. Follow
`docs/AI_LOCAL_DEVELOPMENT.md` for synthetic-data testing, server-only key setup
and provider restrictions. The frontend does not need an AI API key. Uncommitted
local AI work must be transferred separately until an approved release includes it.

## 6. Apply database migrations

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
Set-Location ..
```

The current result should report:

```text
0030_doctor_locations (head)
```

Do not run local migration commands against the production database.

## 7. Configure the frontend

```powershell
Set-Location frontend
npm ci
Copy-Item .env.example .env.local
Set-Location ..
```

The normal local frontend configuration is:

```dotenv
NEXT_PUBLIC_API_BASE_URL=/api/v1
HEALTHLINK_BACKEND_ORIGIN=http://127.0.0.1:8000
```

This keeps browser requests same-origin while Next.js forwards local API
requests to FastAPI.

## 8. Start both services

Open two PowerShell terminals.

Backend terminal:

```powershell
Set-Location path\to\HealthLink\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
Set-Location path\to\HealthLink\frontend
npm run dev
```

Open:

- Application: <http://localhost:3000>
- Backend health: <http://localhost:8000/health>

The health response should report the service as healthy and the environment
as development.

## 9. Run verification before committing

Backend dependency and test checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest backend\tests
```

To include PostgreSQL-specific tests, point the explicit test variable at the
disposable test database:

```powershell
$env:HEALTHLINK_TEST_DATABASE_URL="postgresql+psycopg://healthlink_dev:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/healthlink_test"
.\.venv\Scripts\python.exe -m pytest backend\tests
Remove-Item Env:HEALTHLINK_TEST_DATABASE_URL
```

Frontend checks:

```powershell
Set-Location frontend
npm run lint
npm run typecheck
npm test -- --run
npm run build
Set-Location ..
```

Git checks:

```powershell
git diff --check
git status --short
```

## 10. Commit and push ordinary development work

Push a feature branch rather than pushing directly to `main`:

```powershell
git add -A
git commit -m "feat: describe the change"
git push -u origin feature/phase-22
```

Replace the branch and message with values appropriate to the work.

## 11. GitHub Actions and production deployment

For ordinary local development, no Vercel connection is required. The
established production release path is:

```text
approved push to main
    -> GitHub Actions backend and frontend quality gates
    -> production Alembic migration
    -> Vercel build and deployment
    -> production smoke tests
```

Do not deploy directly from a new PC unless there is a specific, reviewed
recovery reason. Obtain explicit owner approval before committing or pushing a
release to `main`, migrating production, or deploying.

If Vercel CLI access is genuinely needed:

```powershell
npm install --global vercel@59.10.0
vercel login
vercel whoami
vercel projects ls
vercel link --yes --project healthlink-sd
```

Confirm the selected owner or team before linking. The generated `.vercel`
directory is machine-specific and ignored by Git.

GitHub CLI is optional. Git authentication can use the normal browser, Git
Credential Manager, SSH, or an appropriately scoped personal access token.

## 12. Security rules

- Never copy or commit an existing `.env` file.
- Never place the production database URL in commands, documentation, tests,
  screenshots, or Git.
- Never run automated tests against production.
- Do not commit production test-account credentials.
- Do not store national identifiers, medical data, credentials, or exact
  coordinates in logs or fixtures.
- Obtain production, Vercel, and GitHub secrets through a secure password
  manager or their respective dashboards.
- Keep exact facility coordinates backend-only.
- Ask before committing, pushing to `main`, migrating production, or deploying.

## 13. Troubleshooting

### Backend cannot connect to PostgreSQL

Confirm PostgreSQL is running, the local database exists, and `DATABASE_URL`
uses the local port, username, password, and database name.

### Frontend cannot reach the API

Confirm FastAPI is listening on port 8000 and `.env.local` contains:

```dotenv
HEALTHLINK_BACKEND_ORIGIN=http://127.0.0.1:8000
```

Restart `npm run dev` after changing frontend environment variables.

### Migration fails on an existing local database

Run:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic current
..\.venv\Scripts\python.exe -m alembic heads
```

Do not downgrade, stamp, or delete the database until the current migration
state and any local data that must be preserved are understood.

### Node version is rejected

Use Node 24.15 or newer within the Node 24 release line. The frontend explicitly
requires Node `>=24.15.0 <25`.

## Authoritative project references

- `AGENTIC_IMPLEMENTATION_HANDOFF_CURRENT.md`
- `README.md`
- `docs/implementation-progress.md`
- `docs/implementation-assumptions.md`
- `docs/VERCEL_GITHUB_ACTIONS_DEPLOYMENT.md`
