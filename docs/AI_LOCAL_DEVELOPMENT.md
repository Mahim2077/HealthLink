# HealthLink AI: local development

Phases 22–31 and the modern-chat upgrade have been released; current production
status is recorded in `AGENTIC_IMPLEMENTATION_HANDOFF_CURRENT.md` and
`PRODUCTION_CHAT_RELEASE_2026_10_20.md`. Saved conversations require migration
`0031_ai_conversations`, now applied to production and the synthetic local QA database.
See `AI_CONVERSATIONS_2026_10_19.md` for ownership, retention and consent details.

## Safe end-to-end development

Use a dedicated local database containing only synthetic citizens and records.
Set these **backend-only** environment variables, then restart FastAPI:

```dotenv
AI_ENABLED=true
AI_PROVIDER=mock
AI_RECORD_CONTEXT_ENABLED=true
AI_TIMEOUT_SECONDS=20
AI_MAX_INPUT_CHARACTERS=12000
AI_MAX_CONTEXT_RECORDS=10
```

The mock needs no API key and makes no external requests. It exercises the same
authentication, consent, context, audit, output-validation and rendering path.
Its generic responses deliberately do not simulate medically meaningful advice.
The frontend uses the existing same-origin `/api/v1` proxy; no AI key belongs in
frontend settings or in Git. Set `HEALTHLINK_BACKEND_ORIGIN` for a separate local
backend, if needed. Keep existing secret files out of source control.

## GroqCloud adapter — selected provider

The owner selected GroqCloud on 2026-10-02 after discussing Qwen 3.8. Backend
defaults/templates now select Groq with AI still disabled. Configure the ignored
`backend/.env` for **synthetic-data local testing**, then restart FastAPI:

```dotenv
AI_ENABLED=true
AI_PROVIDER=groq
AI_API_KEY=YOUR_GROQ_API_KEY
AI_MODEL=qwen/qwen3.8-27b
AI_RECORD_CONTEXT_ENABLED=true
```

`YOUR_GROQ_API_KEY` is a placeholder, not a key to commit. This uses the existing
`httpx` dependency to call Groq's fixed HTTPS chat-completion endpoint directly;
no OpenAI API account, OpenAI SDK or extra Groq SDK is needed. There is no
automatic provider fallback, streaming, tool execution, or retry loop. Qwen
thinking is disabled to avoid spending the output budget on hidden reasoning.
One 2,048-token completion limit and both HTTP/total deadlines bound each request.

Run the normal FastAPI entry point (`app.main:app`) for this configuration.
The temporary ignored `.runtime/phase27-qa-app.py` launcher deliberately overrides
settings with an isolated synthetic database and mock AI; it does not read
`backend/.env`. The browser acceptance preview at port 3001 used that mock
launcher, not a live Groq request. Stop the temporary QA backend before starting
a normal backend on the same port, and point the frontend proxy at that backend.

Groq's strict JSON-schema mode requires every property to be required and every
object to forbid extra properties. The adapter normalizes the wire schema,
including nested/nullable fields, while original Pydantic validators still check
all lengths, ranges and types afterwards. Shared safety/grounding validation and
record access/consent controls apply unchanged to every provider.

`AI_MODEL` remains replaceable, but replacements must support Groq's **strict
JSON-schema output**. Unsupported/unavailable models fail safely; the app does
not silently fall back to unconstrained text/JSON or another provider. When
switching back to Gemini, also change `AI_MODEL` to a Gemini-compatible model.
If no model is configured, code selects a provider-appropriate default.

[Groq lists Qwen 3.8 as a preview model](https://console.groq.com/docs/model/qwen/qwen3.8-27b)
and [documents its strict-schema support](https://console.groq.com/docs/structured-outputs).
Actual key validity, account model access, quota and real-model output quality
have **not** been verified. All adapter tests intercept HTTP in memory, send only
synthetic information, and make zero external model requests.

### Health-data rollout is a separate decision

[Groq's service agreement](https://console.groq.com/docs/legal/services-agreement)
includes medical/professional-advice restrictions and a PHI/BAA condition. Do not
assume all Bangladesh health records automatically fall under US HIPAA, or that
citizen consent settles provider/legal requirements. Resolve the actual product
scope and applicable obligations before a real-patient rollout.
[Groq's data controls](https://console.groq.com/docs/your-data) describe exceptions
to default inference non-retention and optional Zero Data Retention. This adapter
does not configure or guarantee account-level ZDR, accept agreements, or send
real patient records as part of development. Keep both enable flags off in
production pending separate approval and privacy/terms review.

## Native Gemini adapter — optional alternative

The replaceable provider configuration is `AI_PROVIDER=gemini`, `AI_API_KEY`
(server-only), and `AI_MODEL`. The installed/tested Google GenAI SDK is 1.75.0;
requirements allow compatible 1.75+ releases below 2.0. A restart loads changed
settings. The model must support JSON structured output. Actual key validity,
quota, model access and live model behaviour must be tested separately; no real
Gemini generation was made during this implementation's acceptance tests.

Adding a key alone does not enable AI: `AI_ENABLED` is a separate switch, and
record transfer additionally requires `AI_RECORD_CONTEXT_ENABLED`. Defaults are
disabled. Do not publish a key as `NEXT_PUBLIC_*`, in a screenshot, or in a log.

### Provider restrictions are not solved by consent

[Google's current API terms](https://ai.google.dev/gemini-api/terms), reviewed
2026-10-02, prohibit sending sensitive/confidential/personal information to unpaid
services, and prohibit clinical-practice/medical-advice use. Paid-service data-use
terms differ, but the medical-use restriction still needs review. The terms also
restrict API clients likely to be accessed by under-18s. Do not enable a real-data
Gemini rollout merely because a citizen checked a consent box.

Keep live-provider testing limited to synthetic information and an allowed
informational use case. Before production enablement, resolve provider terms,
age/access rules, privacy requirements and product scope with the owner.

## UI entry points

- Citizen prescription detail: secondary “Explain with AI” action.
- Citizen finalized diagnostic report: secondary explanation below source results.
- Citizen medical history: optional summary with per-request record opt-in.
- Citizen navigation → AI assistant: general questions or record-aware questions.
- AI assistant → Symptom guidance: structured, non-diagnostic information without
  loading health records automatically. Do not wait for AI in an emergency.

Requests have bounded inputs/outputs. Authenticated responses use private/no-store
cache headers. The approved conversation interface now saves questions and
validated answers privately to the citizen's account, with delete controls.
No browser chat persistence is used. Other explanations remain transient;
metadata-only `AI_ACCESS` logs capture record retrieval. GENERAL and symptom
modes do not create clinical context or record-read audits. General follow-ups
never resend prior record-aware history without fresh record consent.

## Accuracy and privacy limitations

### Explanation-only system policy

`backend/app/ai/policy.py` is the shared server-owned system instruction used by
both Groq and Gemini. AI may explain terminology, documented conditions, lab
concepts and the general purpose/mechanism of medicines already named in a
question or authorized prescription. It must never diagnose, create a
prescription, recommend medicines/alternatives, invent medication schedules or
tell a patient to start/stop/change treatment. User questions and record text
cannot override the system policy, including through role-play or translation.

Prescription explanations now receive the authorized visit's recorded condition
and may return optional `medicine_education` keyed to existing medicine item
numbers. Duplicate/foreign item numbers are rejected. The UI labels this as
general knowledge, not the doctor's confirmed reason. Actual per-medicine
rationale is not inferred: `purpose_or_role` remains server-owned unknown text
because the record has no authoritative per-medicine rationale field. Medicine
names and instructions are assembled from the original record, not generated.

Output checks include unfamiliar-condition/medicine directives, dose schedules,
simple formatting evasions and selected Bangla patterns. Each text field is
validated separately. These conservative checks can reject benign phrasing and
are not a complete multilingual or semantic safety guarantee. Review live model
behaviour separately with synthetic data before considering enablement.

Direct identity fields are omitted, and common identifiers/known identity terms
are redacted from text. This is identity reduction, not guaranteed anonymization:
arbitrary free text can still identify a person or include sensitive details.
Schema, source-category and safety-language checks reject many unsafe responses,
but cannot prove model statements correct or catch all diagnoses/treatment advice.
Clinical records remain authoritative; no AI response may mutate them.

The server retains original lab results/ranges/flags and prescription instructions
instead of delegating those facts to the model. It refuses invented lab parameters
and new numerical claims. There is no medically validated automated triage system.

## Quality gates

Current checkpoint (2026-10-17): **532 backend tests / 263 frontend tests passed**,
lint/typecheck/production build passed, eight real-browser production-build cases
and nine live synthetic AI/UI cases passed. See
`PHASE_31_LOCAL_RELEASE_REPORT.md` for scope and external/manual limits. Earlier
runtime-unavailable statements below are historical. The two live safety
rejections were fixed by omitting structured medicine directions from explanation
input and prohibiting schedule echoes, never by weakening validation. Unchanged
prescription instructions are still assembled by the server and displayed in UI.

Latest local verification (2026-10-02, explanation-policy update): **476 backend
tests passed, zero skipped** against dedicated local PostgreSQL 17.6; **55
frontend files / 252 tests passed**, lint, TypeScript and production build passed.
Regression tests cover the previously accepted unsafe diagnosis/prescribing
probe, general-education/source separation and unknown/duplicate medicine items.
Whitespace checks passed. One upstream Starlette/httpx deprecation warning remains.

Earlier mock-only browser acceptance passed all citizen AI entry points,
per-request consent, source preservation and metadata-only audits, with no browser
errors or narrow-viewport overflow. A fresh browser check after this policy/UI
change could not complete: the browser controller timed out twice while binding
the existing local tab. Do not represent the earlier check as fresh browser
acceptance of this update. No live Gemini/Groq generation, production-data test
or deployment was performed.

Run the full backend suite against a dedicated local PostgreSQL test database;
apply migrations and `alembic check` first. Run frontend tests, lint, TypeScript,
production build and browser acceptance with synthetic data. CI must use mocks,
not live API spending. See the latest phase ledger for exact evidence.

Commit, push, deploy and enabling production AI require fresh owner authorization.
