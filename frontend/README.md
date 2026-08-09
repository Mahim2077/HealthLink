# HealthLink frontend

Phase 0 establishes the shared Next.js frontend foundation. It intentionally contains no authentication or portal workflows from later phases.

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

## Phase 0 assumptions

- System fonts are used so builds remain deterministic without downloading font files.
- Vitest and Testing Library provide lightweight component and configuration tests.
- Access tokens, refresh behavior, route guards, and portal pages begin in their documented later phases.
