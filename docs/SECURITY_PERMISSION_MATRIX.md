# HealthLink security and permission matrix

Status: 2026-10-17. This describes local code and regression coverage, not a
production security certification. The current released baseline is still
Phases 15–21 plus the approved discovery/clinical improvements.

## Authority rules

The backend authorizes every request from the authenticated session, portal and
selected professional registration. UI visibility is not authority. A historical
read grant never authorizes a clinical write. Returning a summary/AI explanation
does not expand access to its underlying record.

| Actor or request | Required boundary | Regression evidence in `backend/tests/` |
| --- | --- | --- |
| Anonymous | Protected clinical, dashboard and AI routes deny access | `test_auth_dependencies.py`, `test_dashboard_security.py`, AI route tests |
| Citizen token | No Professional/Admin privileges; own citizen profile only | `test_dashboard_security.py`, `test_professional_routes.py`, `test_admin_routes.py` |
| Admin token | Operational access only; no doctor clinical privileges | `test_dashboard_security.py`, `test_visits.py`, `test_prescriptions.py` |
| Inactive account/admin | No protected operational or clinical access | `test_auth_dependencies.py`, `test_dashboard_security.py` |
| Pending/rejected professional | Selected-role restrictions remain enforced | `test_professional_routes.py`, `test_dashboard_security.py` |
| Wrong selected role or stale role claim | No inheritance from another registration | `test_professional_login.py`, `test_access_grants.py`, AI tests |
| Lab technician | No doctor chamber, consultation or prescription authorship | `test_chamber.py`, `test_visits.py`, `test_prescriptions.py` |
| Doctor | Cannot author lab results using the doctor role | `test_lab_reports.py` |
| Waiting or unrelated patient | No CURRENT-patient record access | `test_visits.py`, `test_diagnostics.py`, `test_medical_history.py` |
| Stale CURRENT queue entry | Requires BOOKED appointment and ACTIVE session, with matching doctor/facility/date | `test_dashboard_security.py`, `test_access_grants.py` |
| Citizen record ID | Cross-citizen prescription, report, history and AI access denied | `test_prescriptions.py`, `test_lab_reports.py`, AI tests |
| Manual grant | Exact resource scope; expiry, revocation, role and account checked | `test_access_grants.py` (every scope/resource pair) |
| Prescription read grant | Never permits editing or creates a CURRENT relationship | `test_access_grants.py`, `test_prescriptions.py` |
| Prescription author | Existing author-only edit rules; finalized visit fields stay immutable | `test_prescriptions.py`, `test_release_journey.py` |
| Lab assignment | Exact active lab registration, assigned test and active facility | `test_diagnostics.py`, `test_lab_reports.py`, `test_dashboard_security.py` |
| Finalized lab report | Immutable; finalization and test completion are atomic | `test_lab_reports.py` (including rollback on commit failure) |
| Prescription PDF | Reauthorize every request, render fresh bytes, private/no-store, no stored PDF/document row | `test_prescriptions.py`, `test_release_journey.py` |
| AI record ID | Existing record policy rechecked; no model-controlled scope | `test_ai_clinical_explanations.py`, `test_ai_assistant_phases_25_27.py` |
| GENERAL AI | Loads no clinical records | `test_ai_assistant_phases_25_27.py` |
| RECORD_AWARE AI | Explicit opt-in and bounded authenticated-citizen context; no foreign patient ID | `test_ai_foundation.py`, `test_ai_assistant_phases_25_27.py` |
| AI output | Explanation only; no diagnosis, prescribing, treatment changes or guessed doctor intent | `test_ai_generation.py`, `test_ai_clinical_explanations.py`, `test_ai_groq.py` |
| Refresh/logout | Rotation/replay and concurrent-session boundaries checked | `test_auth_service.py`, `test_auth_routes.py`, `test_auth_postgresql.py` |

Citizen draft visibility is resource-specific: existing owned-prescription reads
are preserved, but lab drafts are never citizen-readable and dashboard/history
summaries expose finalized clinical work only.

## Input and resource bounds

| Surface | Enforced limit |
| --- | --- |
| Visit/combined prescription free text | 4,000-character complaint/diagnosis/follow-up; 8,000-character notes/advice fields |
| Prescription medicines | At most 50 rows; bounded name, dose, frequency, duration and instructions |
| Lab report | 1–100 rows; 10,000-character summary; bounded individual results and finite numeric precision |
| Diagnostic lists | Page 1–10,000; page size 1–100 (API default 50, UI 20); stable ordering; explicit `has_next` |
| New doctor dashboard | At most 10 chamber projections plus a `chambers_has_more` indicator; aggregate counts, not full patient lists |
| Admin identity search | At least one filter; at most 50 results; bounded identity fields |
| AI question/chat/symptoms | 1,500 characters; server context/input budgets also apply |
| AI configured input/context | Default 12,000 characters / 10 records; configuration caps 50,000 / 25; per-record text is bounded |
| AI provider | Deadline, output budget, schema validation; no automatic retries, tools, redirects or provider fallback |
| Future release smoke | Nine read-only probes per origin, bounded response size/time/retries; no login or model invocation |

These are reviewed boundaries, not a claim that every historical list endpoint
has been converted to pagination. Do not silently truncate legacy operational
queues; review their consumers before changing their contracts.

## Privacy, logging and caching

- Dashboard DTOs omit patient names, contact details, diagnoses and clinical
  notes. The doctor sees serial numbers; opening a record reauthorizes access.
- Sensitive components remount on session/role change and ignore late responses.
- Authenticated responses and login/refresh responses use `private, no-store`;
  API responses use `X-Content-Type-Options: nosniff`.
- Validation responses redact submitted `input`, including arbitrary medical
  free text. SQLAlchemy engines hide bound values in exception strings.
- The admin UI sends identity-search filters in a POST body. The deprecated GET
  compatibility endpoint remains: old clients can still put identifiers in a
  URL. Do not claim that this legacy path is log-safe; review its retirement and
  infrastructure access-log redaction before real-data release.
- Clinical audits contain metadata, not prompts, chat messages, raw clinical
  records or model responses. AI identity reduction is not anonymization.
- No process-local limiter is presented as a global serverless rate limiter.
  Provider 429 handling exists; shared/platform abuse controls need a separate
  deployment-level decision if required.
- No new reminder scheduler, stored PDF, browser chat persistence or automatic
  clinical write is introduced.

## Remaining release checks

Production logs have **not** been inspected for this unreleased code. During an
authorized release, inspect a bounded window without copying secret/PHI-bearing
lines into chat or artifacts. Check password, NID/BCN, bearer/refresh credentials,
database URL, provider key, legacy Blob token, clinical text and prompt leakage.
Also review CI credential exposure and third-party observability settings.

Live Groq key/model/quota, current provider terms, medical/Bangla answer quality,
and health-data handling remain unverified. Both AI enable flags stay off by
default. Prompts and text guards are defence in depth, not semantic guarantees.
