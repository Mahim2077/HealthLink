# HealthLink single-project Vercel deployment

This guide deploys the existing HealthLink monorepo as one Vercel project named
`healthlink-sd` through GitHub Actions.

The production surface is:

| URL | Service |
| --- | --- |
| `https://healthlink-sd.vercel.app/` | Next.js frontend |
| `https://healthlink-sd.vercel.app/api/v1/*` | FastAPI backend |
| `https://healthlink-sd.vercel.app/health` | FastAPI health check |
| `https://healthlink-sd.vercel.app/docs` | FastAPI API documentation |

The Vercel project and its stable production domain are both named
`healthlink-sd`. A separately owned custom domain can be attached later.

Nginx is not used. Vercel does not run a persistent reverse-proxy process.
Instead, Vercel Services builds `frontend/` and `backend/` independently and
merges their routes behind the same project domain according to the root
`vercel.json`.

### Current Vercel setup state (2026-09-04)

- Vercel CLI 59.10.0 is authenticated locally as `mahimchow2077-3904`.
- `mahimchow2077-3904s-projects/healthlink-sd` has been created and linked to the
  repository root.
- Vercel reports the project Framework Preset as **Services**.
- Production config values, a generated 48-byte JWT secret, and the authorized
  Supabase connection are configured. Prepared statements are disabled for the
  transaction pooler on port 6543.
- Vercel's optional automatic GitHub connection failed. This does not block the
  documented GitHub Actions path, but the GitHub secrets are still required.
- The owner explicitly authorized a direct bootstrap deployment of the current
  worktree. Deployment `dpl_3EGupRwXyCFYHNcij6ArrEMz6GJJ` is live at
  `https://healthlink-sd.vercel.app`.
- Phase 13 includes its frontend and private production Blob adapter. Commit
  `ea07255` passed GitHub Actions run 8 and deployed through the documented
  pipeline. The stable-domain prescription/PDF production verification passed.
- The local CI gates are green: 195 backend tests pass (33 PostgreSQL-only
  tests skip without their dedicated test URL), all 169 frontend tests pass,
  lint/type-check/build pass, and `alembic check` reports no metadata drift.

## 1. Understand the deployment gate

The workflow in `.github/workflows/ci-cd.yml` performs this sequence:

1. Start PostgreSQL 17 in GitHub Actions.
2. Install the backend dependencies.
3. Upgrade the CI database through the repository's Alembic head.
4. Run `alembic check` and the complete backend test suite.
5. Run frontend lint, TypeScript, Vitest, and production-build checks.
6. On `main` only, upgrade the production database.
7. Build both Vercel Services.
8. Deploy one prebuilt production application.
9. Smoke-test `/` and `/health`.

Pull requests run only the CI jobs. They do not migrate production or deploy.
A push to `main`, or a manual run on `main`, can deploy only after both CI jobs
pass.

### Current repository checkpoint

At the time this deployment snapshot was prepared:

- The production PostgreSQL database and repository migration chain are both
  at `0023_prescription_documents`.
- Phase 13 backend, frontend, authorization, and storage-adapter tests pass.
- A private Vercel Blob store is connected to production, and the backend
  selects it with `PRESCRIPTION_STORAGE_BACKEND=vercel_blob`.
- The local filesystem adapter remains development-only.

The workflow deliberately retains every quality gate. The first production
snapshot was released directly through Vercel CLI only because the owner
explicitly requested a bootstrap deployment. Continuous deployment now
publishes verified `main` commits; Phase 13's GitHub Actions deployment and
stable-domain prescription/PDF flow both passed. Do not downgrade or rewrite
the existing database; database state and deployed source migration history
must remain aligned.

## 2. Obtain Vercel Services access

This deployment uses Vercel Services because the repository contains two
frameworks under separate roots. Services is currently access-controlled while
in private beta.

1. Sign in to the Vercel account that should own HealthLink.
2. Open the Vercel Services documentation and request/enable access for the
   account or team.
3. Confirm that **Services** appears as an available Framework Preset when
   creating or configuring a project.

If the account cannot enable Services, this exact single-project layout cannot
be deployed through the supported Services configuration. The safe fallback is
two Vercel projects with a same-origin proxy, not Nginx.

## 3. Authenticate and create the Vercel project

Use the Vercel CLI from the repository root:

```powershell
npm install --global vercel@latest
vercel login
Set-Location D:\HealthLink_V_1
vercel link
```

Use Node.js 24.15 or newer within the Node 24 release line. The frontend
dependency lockfile and the Vercel project both target Node 24.

During `vercel link`:

1. Select the correct personal account or team.
2. Create a new project if it does not exist.
3. Request the project name `healthlink`.
4. Link the repository root—not `frontend/` or `backend/` separately.

Open the linked project in the Vercel dashboard and set its Framework Preset to
**Services**. The repository's `vercel.json` declares:

- `frontend/` as the `nextjs` service;
- `backend/` as the `fastapi` service using `app.main:app`;
- `/api/v1`, `/health`, `/docs`, `/redoc`, and `/openapi.json` as backend
  routes;
- all remaining paths as frontend routes.

The generated `.vercel/project.json` contains `orgId` and `projectId`. The
`.vercel/` directory is ignored and must never be committed.

## 4. Configure Vercel environment variables

In **Vercel project → Settings → Environment Variables**, add the following to
the Production environment. Add them to Preview as well only if preview
deployments are introduced later.

| Variable | Production value or guidance |
| --- | --- |
| `APP_NAME` | `HealthLink` |
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `DATABASE_URL` | Production PostgreSQL/Supabase connection URL |
| `DB_DISABLE_PREPARED_STATEMENTS` | `true` for a transaction-mode pooler; otherwise `false` |
| `JWT_SECRET_KEY` | A cryptographically random secret of at least 32 characters |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` |
| `NEXT_PUBLIC_API_BASE_URL` | `/api/v1` |
| `PRESCRIPTION_STORAGE_BACKEND` | `vercel_blob` |
| `BLOB_READ_WRITE_TOKEN` | Automatically added by the linked private Vercel Blob store; treat as sensitive |
| `PRESCRIPTION_STORAGE_PATH` | Not used in production; optional local-development path only |

Vercel Services supplies a service-aware `FRONTEND_URL` for the service named
`frontend`. This project also sets it explicitly to
`https://healthlink-sd.vercel.app`; update it and redeploy if the domain
changes.

Do not put these values into `.env.example`, workflow YAML, source code, commit
messages, or GitHub Actions logs. Configure `DATABASE_URL` and
`JWT_SECRET_KEY` as sensitive values.

Generate a JWT secret locally without printing it into shell history:

```powershell
$bytes = New-Object byte[] 48
[System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
$secret = [Convert]::ToBase64String($bytes)
$secret | Set-Clipboard
Remove-Variable secret, bytes
```

Paste the clipboard value directly into Vercel and GitHub secret forms.

### Prescription PDF storage

Vercel Functions have an ephemeral filesystem, so production must not select
the local adapter. Create and link a private Blob store, retain its generated
`BLOB_READ_WRITE_TOKEN`, and set `PRESCRIPTION_STORAGE_BACKEND=vercel_blob`.
The backend uses versioned private objects and serves bytes only through the
authorized `/api/v1/prescriptions/{id}/pdf` route.

## 5. Create the Vercel access token

In the Vercel account:

1. Open **Account Settings → Tokens**.
2. Create a token dedicated to GitHub Actions.
3. Scope it to the account/team that owns `healthlink`.
4. Copy it once and store it as the GitHub secret `VERCEL_TOKEN`.

Do not paste the token into this document or into chat.

## 6. Configure GitHub Actions secrets

Open the GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

Create:

| GitHub secret | Source |
| --- | --- |
| `VERCEL_TOKEN` | Dedicated Vercel access token |
| `VERCEL_ORG_ID` | `orgId` from `.vercel/project.json` |
| `VERCEL_PROJECT_ID` | `projectId` from `.vercel/project.json` |
| `PRODUCTION_DATABASE_URL` | The same production database used by the backend |

If GitHub CLI is installed, each command below securely prompts for its value:

```powershell
gh secret set VERCEL_TOKEN
gh secret set VERCEL_ORG_ID
gh secret set VERCEL_PROJECT_ID
gh secret set PRODUCTION_DATABASE_URL
```

Create a GitHub environment named `production` under:

**Settings → Environments → New environment**

Recommended protection:

- allow deployments only from `main`;
- require a manual reviewer while the project remains pre-production;
- prevent administrators from bypassing the rule when practical.

The workflow declares the `production` environment for both migration and
deployment jobs.

## 7. Avoid duplicate deployments

This repository deploys through GitHub Actions using:

```text
vercel pull
vercel build --prod
vercel deploy --prebuilt --prod
```

If the Vercel project is also connected through Vercel's automatic Git
integration, disable automatic production deployments or disconnect the Git
integration. Otherwise one push may produce both a Vercel-managed deployment
and a GitHub-Actions-managed deployment.

## 8. Commit safely

Review the worktree and stage only the files intended for the current phase:

```powershell
git status --short
git diff --check

git add -- `
  .github/workflows/ci-cd.yml `
  .vercelignore `
  vercel.json `
  .gitignore `
  .env.example `
  backend/.env.example `
  backend/.python-version `
  frontend/package.json `
  frontend/package-lock.json `
  frontend/src/lib/api/config.ts `
  frontend/src/lib/api/config.test.ts `
  README.md `
  docs/implementation-assumptions.md `
  docs/VERCEL_GITHUB_ACTIONS_DEPLOYMENT.md
```

Inspect the staged set before committing:

```powershell
git diff --cached --stat
git diff --cached
```

Suggested infrastructure commit:

```powershell
git commit -m "ci: add single-project Vercel deployment pipeline"
git push origin main
```

Only push directly to `main` if that matches the repository's collaboration
policy. Otherwise push a `codex/vercel-cicd` branch, open a pull request, let CI
run, and merge it after review.

## 9. Observe the workflow

Open **GitHub → Actions → HealthLink CI/CD**.

Expected jobs:

```text
Backend quality gates ─┐
                       ├─> Migrate production database ─> Deploy healthlink
Frontend quality gates ┘
```

If either quality job fails, production remains unchanged. If the migration
fails, Vercel deployment does not start. The final job records the generated
deployment URL in the GitHub Actions summary.

## 10. Verify the live deployment

After a successful workflow, open:

```text
https://healthlink-sd.vercel.app/
https://healthlink-sd.vercel.app/health
https://healthlink-sd.vercel.app/docs
```

Also verify these browser flows:

1. Citizen registration and login.
2. Refresh the page and confirm the session restores through the HttpOnly
   refresh cookie.
3. Citizen dashboard/profile.
4. Professional login and verified-doctor portal.
5. Admin login and authorization guards.
6. Doctor search, appointment booking, chamber queue, and consultation.
7. Directly opening a protected portal while signed out redirects or denies
   access correctly.
8. Browser console contains no application or CORS errors.

The frontend must call `/api/v1` on the same hostname. If browser requests go
to `localhost:8000` or a second Vercel hostname, check the production value of
`NEXT_PUBLIC_API_BASE_URL` and redeploy.

## 11. Custom domain

The project currently uses Vercel's generated project domain:

```text
healthlink-sd.vercel.app
```

For a domain you own:

1. Open **Vercel project → Settings → Domains**.
2. Add the complete domain, such as `healthlink.example` or
   `app.healthlink.example`.
3. Add the DNS records Vercel displays at the registrar.
4. Change any explicitly configured `FRONTEND_URL` to the new HTTPS origin.
5. Redeploy so the backend CORS setting and generated frontend values agree.

Because frontend and backend remain in one project, `/api/v1` and refresh
cookies continue to use that same custom origin.

## 12. Rollback

Application rollback:

1. Revert the faulty Git commit and merge/push the revert to `main`; or
2. promote a known-good deployment from the Vercel dashboard.

Database migrations are intentionally not downgraded automatically. A code
rollback must remain compatible with the migrated schema. Treat any destructive
database rollback as a separately reviewed operation with a backup.

## Troubleshooting

### Vercel rejects the `services` property

The account does not have Services enabled, or the project Framework Preset is
not **Services**. Request access and confirm the preset before retrying.

### Backend CI fails at `alembic check`

Import every active ORM model package in `backend/alembic/env.py` and reconcile
constraint/index metadata with the migrations. Do not remove the check from CI
to conceal drift.

### Production migration says it cannot locate revision 0023

The database has been migrated using Phase 13 files that are not present in
the Git commit being deployed. Finish and commit the matching migration chain,
or use a separate compatible database. Do not stamp or downgrade blindly.

### Login succeeds but refresh does not survive reload

Confirm that the browser calls the same-origin `/api/v1` URL, the production
deployment uses HTTPS, and no second backend hostname is configured. Inspect
the refresh cookie path—it must remain `/api/v1/auth`.

### Database connections are intermittent

Use the provider's serverless/transaction-pooler connection string. Set
`DB_DISABLE_PREPARED_STATEMENTS=true` when required by that pooler, keep TLS
enabled in the URL, and place the Vercel function region near the database.

### Prescription PDF disappears

Confirm production still has `PRESCRIPTION_STORAGE_BACKEND=vercel_blob` and a
valid `BLOB_READ_WRITE_TOKEN`. The local-storage adapter is development-only
and must never be selected on Vercel's ephemeral filesystem. Check the private
`healthlink-prescriptions` store and function logs without exposing storage
tokens or raw object keys.

### Local Windows `vercel build` reports a missing lambda

On this workstation, Vercel CLI 59.10.0 under Node 24 completes the Next.js
compile and then reports `Unable to find lambda for route` for a prerendered
App Router page. The same error family has been reported against local Vercel
builds even when Next.js itself succeeds. Do not work around it by forcing
unrelated pages to be dynamic. The authoritative prebuilt check for this
repository is the Linux GitHub Actions `vercel build --prod` job; keep the job
failing if it reproduces there and diagnose its build artifact before deploy.

## Official references

- [Vercel Services](https://vercel.com/docs/services)
- [Vercel Services routing](https://vercel.com/docs/services/routing)
- [Next.js + FastAPI Services starter](https://vercel.com/templates/fast-api/next-js-fastapi-starter)
- [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
- [Vercel deployments from GitHub Actions](https://vercel.com/kb/guide/how-can-i-use-github-actions-with-vercel)
- [Vercel environment variables](https://vercel.com/docs/environment-variables)
- [Vercel ignored deployment files](https://vercel.com/docs/deployments/vercel-ignore)
- [GitHub encrypted secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions)
