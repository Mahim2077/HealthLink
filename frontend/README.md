# HealthLink frontend

Phases 0 and 1 establish the shared Next.js frontend and authentication foundation. It intentionally contains no citizen, professional, or admin login pages from later phases.

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

## Foundation assumptions

- System fonts are used so builds remain deterministic without downloading font files.
- Vitest and Testing Library provide lightweight component and configuration tests.
- Login forms and portal workflows begin in their documented later phases.
