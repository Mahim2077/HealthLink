# HealthLink frontend

The shared Next.js frontend includes the authentication foundation and the Phase 2 Citizen Portal account flow. Professional and admin portal workflows are intentionally not implemented yet.

## Local setup

1. Copy .env.example to .env.local if the backend API uses a different address.
2. Install dependencies with npm install.
3. Start development with npm run dev.

The default frontend address is http://localhost:3000. The default API base URL is http://localhost:8000/api/v1.

## Quality commands

    npm run lint
    npm run typecheck
    npm test
    npm run build

## Authentication foundation

- Access tokens exist only in the in-memory access-token store.
- Refresh tokens are expected in backend-issued HttpOnly cookies and every refresh request includes credentials.
- The API client retries one unauthorized request after a single-flight refresh, preventing concurrent requests from rotating the same refresh session more than once.
- Logout and logout-all close the refresh gate, await any in-flight refresh response, use the latest bearer for termination, and clear memory before releasing the gate.
- Session replacement is serialized through the same barrier for later login flows, preventing login, logout, and refresh cookie responses from racing each other.
- JWT payload decoding supports portal-aware presentation only; backend checks remain authoritative.

## Citizen Portal

- `/citizen/register` creates a citizen account using exactly one NID or Birth Certificate Number, then sends the citizen to sign in. Registration does not create a browser session.
- `/citizen/login` replaces any existing session through the serialized auth barrier and opens the citizen dashboard.
- `/citizen/dashboard` restores a session through the backend refresh cookie after reload, requires a Citizen portal token for presentation, and loads the authorized citizen profile and self-identity endpoints.
- Identity values are masked in the dashboard. Raw identity data is used only in the authorized response and never persisted in browser storage.

## Foundation assumptions

- System fonts are used so builds remain deterministic without downloading font files.
- Vitest and Testing Library provide lightweight component and configuration tests.
- NID and Birth Certificate Numbers are treated as opaque strings. The UI enforces only the documented nonblank and maximum-length rules; government-specific formats remain outside this phase.
