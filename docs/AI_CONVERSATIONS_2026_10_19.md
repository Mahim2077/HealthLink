# Private AI conversations — local implementation

> Release update, 2026-10-20: the owner separately authorized commit, push and
> production deployment. The local-only statements below describe the original
> implementation checkpoint. Follow `PRODUCTION_CHAT_RELEASE_2026_10_20.md` for
> current migration/deployment status; preserve the standard CI release gates.
> Release completed successfully: application `21e94a5`, production migration
> `0031_ai_conversations`, Actions `39398090813`. The original local hold is historical.

The owner approved the revised hybrid chat design and explicitly selected
account-private saved conversations with delete controls. This supersedes the
earlier component-memory-only chat policy. This work is **local and unreleased**:
no commit, push, production migration, environment change or deployment is authorized
by the UI approval. The production application/database remain at the previous release.

## User experience

- Conversation sidebar grouped into Today, Yesterday and Earlier, with paginated
  older history, New conversation and confirmation before permanent deletion.
- Real question/answer transcript, follow-ups, timestamps, source labels, copy
  response, empty/loading/error states, and a scrollable message area.
- Compact “General · Records off” control above the pinned composer. Expanded
  settings disclose external processing and offer one-request record consent.
- Consent resets on edits, attempted sends, conversation changes and successful
  responses. Success returns the composer to General mode. Failed questions are
  preserved for an explicit retry, with the same request identifier.
- Mobile conversation drawer; existing portal chrome and symptom guidance retained.
- No streaming is claimed: the existing bounded structured-response API is used.

## Storage and API

Migration `0031_ai_conversations`, following `0030_doctor_locations`, adds
`ai_conversations` and `ai_conversation_turns`. Both use citizen ownership;
turns store the submitted question, validated AI response, mode and timestamps.
There is no stored raw record-context snapshot and no clinical-record write.
Titles are derived from the first question, not another model call.

Citizen-only endpoints, all private/no-store:

- `GET /api/v1/ai/conversations?offset=0` — 30 summaries per page.
- `GET /api/v1/ai/conversations/{id}` — owned conversation, at most 50 turns.
- `DELETE /api/v1/ai/conversations/{id}` — hard-delete the conversation and turns.
- `POST /api/v1/ai/conversation-messages` — create on first successful answer or
  append; body includes `conversation_id` (nullable), `client_request_id` (UUID),
  `message`, `mode` and `use_my_health_records`.

The previous stateless `POST /api/v1/ai/chat` remains compatible. Existing
prescription/report explanation, history-summary and symptom APIs are unchanged.
History reads/deletion remain available when AI generation is disabled.

Every list/read/send/delete uses the authenticated citizen, never a client-supplied
owner. Foreign conversation IDs return 404; professionals/admins cannot read chats.
An owner/request unique key prevents duplicate saved turns on retry. Existing chats
are reauthorized/locked after generation, including after independently committed
record-access audits, so a concurrently deleted chat cannot be resurrected.

## Privacy, safety and bounded context

Questions and generated answers are now sensitive account data, stored in the
application database until the citizen deletes them. No browser localStorage or
sessionStorage is used for chats. Deletion removes live database rows; it does
not imply immediate erasure from existing infrastructure backups, or from any
configured external provider's retention. Existing database transport/at-rest
controls apply; no separate application-level message encryption was introduced.
Clinical audits remain metadata-only, not a second copy of chat contents.

Follow-up context uses only the last three server-owned turns, at most 500
characters per question/answer, identity-reduced before provider transmission.
The configured total prompt budget is still enforced; older context is dropped
before rejecting the current question. History is explicitly untrusted context,
not clinical evidence, and cannot override the explanation-only system policy.

General mode loads no HealthLink medical records. Once a conversation contains a
record-aware turn, General requests send **no previous conversation context**,
including later follow-ups that might refer to private record-derived details.
The transcript remains visible to its owner. Fresh record consent allows bounded
history plus newly authorized finalized records for that request only.

AI still must not diagnose, prescribe, recommend medication changes, rewrite
directions, book appointments or write clinical records. Existing output safety,
grounding and provider gates are preserved. These safeguards do not prove clinical
accuracy or establish a medically validated triage service.

## Verification and release handoff

Use only the dedicated synthetic local PostgreSQL database for QA. The migration
was applied there and `alembic check` found no schema drift. Production must
receive this migration through the existing approved release workflow **only
after the owner separately authorizes commit/push/deploy**.

Regression coverage includes private ownership/role gates, persistence, deletion,
retry conflicts, failed-output rejection, pagination, 50-turn cap, bounded/redacted
context, fresh consent, General-mode record-history isolation, deletion during
generation, responsive layout and preserved multi-role clinical journeys.

No production credentials or live AI key are needed for this QA. Mock responses
are intentionally generic; visual screenshots are not evidence of live-model
answer quality. See the latest entry in `design-qa.md` for visual evidence.

Final local results: **564 backend tests**, **57 frontend files / 266 tests**,
lint, TypeScript, optimized build and **9/9 Edge browser journeys** passed.
The optimized preview uses the existing loopback Services proxy: port 3001 routes
the API to the synthetic backend on 8001 and UI to Next production mode on 3003.
An initial direct `next start` preview lacked Services API routing and therefore
failed login; the local routing harness was corrected without changing application
or production routing. The subsequent full optimized-build browser run passed.
The in-app browser could not reconnect to loopback; Edge supplied the authenticated
browser screenshots and end-to-end evidence. Preview ports remain local-only.
