# HealthLink — Agentic AI Implementation Prompt (Phases 0–14)

You are an agentic software-development AI responsible for implementing the HealthLink project.

You will be provided with these two Markdown files separately:

1. `HealthLink — System Context and Developer Documentation`
2. `HealthLink — Synchronized System + Database Design and Full Implementation Plan V6`

Treat these two files as the authoritative references for the project.

Your task is to implement **HealthLink from Phase 0 through Phase 14 only**.

Do **not** implement Phase 15 or any later phase unless I explicitly instruct you to do so in a future request.

---

# Primary Objective

Implement the HealthLink application sequentially from:

```text
Phase 0
through
Phase 14
```

following the architecture, database design, business rules, security model, portal model, workflows, API conventions, frontend conventions, and phase requirements defined in the two reference Markdown files.

The target implementation boundary is:

```text
Phase 0   Project Foundation
Phase 1   Shared JWT Authentication and Refresh Sessions
Phase 2   Citizen Registration and Login
Phase 3   Citizen Profile + One-Time BCN → NID Upgrade
Phase 4   Professional Registration + Role Catalog
Phase 5   Admin Login and Admin Portal
Phase 6   Facility Registry + Professional Verification
Phase 7   Professional Login + Active Role Context
Phase 8   Admin Citizen Identity Support
Phase 9   Doctor Search + Doctor Practice Schedule
Phase 10  Appointment Booking + MAX Serial Assignment
Phase 11  Doctor Daily Chamber Session + Serial Queue
Phase 12  Current Patient Clinical Access + Consultation Workspace
Phase 13  Chamber Prescription Form + Electronic PDF
Phase 14  Finish Appointment + Automatic Next Serial
```

Stop after Phase 14 is fully implemented and verified.

---

# Source-of-Truth Priority

Use the files in this order:

```text
1. HealthLink — Synchronized System + Database Design and Full Implementation Plan V6
   → authoritative technical implementation source

2. HealthLink — System Context and Developer Documentation
   → authoritative conceptual, workflow, and business-context source
```

If an older file, existing prototype, comment, or code pattern conflicts with these documents, follow the two supplied reference files.

If the two supplied reference files appear to conflict, prefer the explicit implementation/database rule in the V6 plan and note the discrepancy in your implementation notes.

Do not silently redesign the architecture.

---

# Scope Discipline

Implement only functionality required for Phases 0–14 and the shared infrastructure those phases genuinely require.

Do not prematurely implement:

```text
Medical History Timeline beyond what Phase 12 consultation requires
Structured Diagnostic Test Workflow
Lab Reports
Lab Trends
Emergency Profile full feature
Medicine Reminders
Appointment Reminder Engine
Medical Access Transparency UI
Manual Patient Access Grants as a full feature
OpenAI integration
AI prescription explanation
AI lab explanation
AI medical summary
Healthcare chatbot
Symptom guidance
Final dashboard consolidation
Production deployment
```

These belong to later phases.

You may create small interfaces/placeholders only where Phase 0–14 architecture requires them, but do not implement later business logic.

Do not expand the product scope with unrelated features.

---

# Required Technology Stack

Use the stack defined by the reference documentation.

## Backend

```text
Python
FastAPI
fastapi[standard]
SQLAlchemy ORM
Pydantic
Pydantic Settings
Alembic
PostgreSQL
JWT
Argon2-compatible password hashing
```

## Frontend

```text
Next.js
TypeScript
TSX
App Router
Tailwind CSS
```

## Database

```text
Neon PostgreSQL
```

Use the environment variable:

```env
DATABASE_URL=
```

Do not hardcode a database URL.

## AI

Do not implement OpenAI functionality during Phases 0–14.

The placeholder may exist:

```env
OPENAI_API_KEY=
```

but it must remain unused until the AI phases.

---


# Dependency Manifest Policy

Maintain **one shared backend Python dependency manifest** for the entire FastAPI modular monolith:

```text
backend/requirements.txt
```

Do **not** create separate dependency files for individual flows, modules, features, or phases such as:

```text
requirements_auth.txt
requirements_citizen.txt
requirements_appointments.txt
requirements_prescriptions.txt
requirements_phase_10.txt
```

Whenever a phase introduces a new Python package:

```text
install the package
verify it is actually required
add it to backend/requirements.txt
keep the dependency manifest synchronized with the working application
```

Do not leave a dependency installed only in the local environment without recording it in `backend/requirements.txt`.

For this project, keep both required runtime and development/test Python dependencies in the same `backend/requirements.txt` unless I explicitly request a later split.

Maintain **one frontend dependency manifest**:

```text
frontend/package.json
```

Whenever a phase introduces a frontend package, add it through the project's package manager so `frontend/package.json` and the corresponding lockfile remain synchronized.

Do not create separate `package.json` files for Citizen, Professional, Admin, appointment, prescription, or other feature flows.

Expected dependency ownership:

```text
backend/requirements.txt
    → all Python dependencies for the FastAPI application and tests

frontend/package.json
    → all Next.js/frontend dependencies and devDependencies
```

Dependency manifests are part of the implementation source of truth.

When reviewing a phase before completion, verify:

```text
all imported third-party Python packages are represented in backend/requirements.txt

all imported frontend packages are represented in frontend/package.json

the lockfile matches frontend/package.json

no obsolete experimental dependency was added unnecessarily
```

If a new dependency is introduced during a phase, updating the appropriate shared manifest is part of that phase's Definition of Done.

---

# Frontend Design Quality Requirement

The frontend must not look like a bare prototype or default starter template.

Build a UI that feels:

```text
Modern
Premium
Polished
Professional
Responsive
User-friendly
Consistent
Accessible
```

The design should feel appropriate for a real healthcare product.

Prioritize:

```text
clear visual hierarchy
clean spacing
strong typography
consistent cards/forms/tables
professional dashboard layouts
responsive mobile/tablet/desktop behavior
accessible contrast
clear validation messages
obvious primary actions
well-designed loading states
useful empty states
friendly error states
subtle transitions/interaction feedback
consistent navigation between portal sections
```

Avoid:

```text
overly flashy animations
visual clutter
excessive gradients
hard-to-read glass effects
tiny text
inconsistent spacing
developer-looking raw forms
default unstyled HTML
unnecessary decorative complexity
```

The interface should look premium without sacrificing usability.

Citizen, Professional, and Admin portals should have distinct context-appropriate navigation while still feeling like parts of the same HealthLink product.

Reuse a consistent design system for:

```text
buttons
inputs
selects
textareas
cards
tables
badges
alerts
dialogs
navigation
page headers
loading states
empty states
error states
```

When implementing each phase, frontend quality is part of the phase definition of done, not an optional cleanup task for later.

---

# Development Method

Use **vertical-slice development**.

For every applicable feature phase, complete the full stack before considering the phase finished:

```text
Database design
    ↓
SQLAlchemy ORM model
    ↓
Alembic migration
    ↓
Pydantic request/response schemas
    ↓
Repository layer
    ↓
Service/business logic
    ↓
FastAPI route
    ↓
Authentication/authorization
    ↓
Frontend TypeScript types
    ↓
Frontend API integration
    ↓
Next.js TSX interface
    ↓
Automated tests
    ↓
Browser/user-flow verification
```

Do not implement several phases' databases first and postpone their APIs/UI until later.

Finish each phase before moving to the next one.

---

# Before Starting Each Phase

Inspect the existing repository.

At minimum inspect:

```text
git status
current directory structure
existing SQLAlchemy models
existing Alembic migrations
Pydantic schema conventions
repository conventions
service conventions
route conventions
authorization dependencies
frontend route structure
frontend components
API client code
tests
```

Reuse established patterns where they are compatible with the reference documentation.

Do not create duplicate abstractions simply because a new phase begins.

---

# Database Rules

Every schema change must use Alembic.

Never manually alter the Neon database and leave the change undocumented.

Required workflow:

```text
update ORM
generate migration
inspect migration carefully
apply migration
run tests
```

Do not proceed if the migration fails.

Use the database constraints described in V6.

Important invariants include:

```text
users.email UNIQUE

NID globally UNIQUE

BCN globally UNIQUE

one citizen profile per user

one professional base profile per user

one role registration per professional + role

BM&DC Registration Number UNIQUE

one doctor practice schedule per weekday

one serial per doctor/facility/date

one queue entry per appointment

at most one CURRENT queue entry per practice session

one medical visit per appointment

one prescription per visit

one prescription PDF/document record per prescription
```

Use PostgreSQL constraints as final consistency protection instead of relying only on frontend/service checks.

---

# Identity Rules

Follow the defined identity model exactly.

There is one base:

```text
users
```

A user may additionally have:

```text
citizen profile
healthcare professional profile
admin account
```

Do not create completely separate citizen and professional user databases.

---

# Citizen Registration Rules

Citizens initially register using exactly one:

```text
NID
OR
Birth Certificate Number
```

Reject:

```text
both supplied
neither supplied
duplicate NID
duplicate BCN
duplicate email
```

BCN is citizen-only.

The authoritative NID location is:

```text
user_national_identifiers
```

---

# BCN → NID Upgrade Rules

BCN-registered citizens may add an NID once.

The frontend must require the user to type exactly:

```text
CONFIRM
```

The backend must independently verify this.

Requirements:

```text
citizen currently has BCN
citizen currently has no NID
submitted NID is globally unique
confirmation == "CONFIRM"
```

After successful upgrade:

```text
BCN remains stored
NID is stored
nid_added_at is recorded
citizen cannot self-change the NID again
```

Do not expose NID/BCN mutation through the normal profile-update endpoint.

---

# Professional Registration Rules

Professional registration requires:

```text
NID
```

Do not allow BCN-based professional registration.

Professionals select a role during registration.

Initial role catalog includes:

```text
DOCTOR
LAB_TECHNICIAN
NURSE
PHARMACIST
RADIOLOGY_TECHNICIAN
OTHER_HEALTHCARE_PROFESSIONAL
```

Professional role registrations begin:

```text
PENDING
```

No professional clinical capability becomes active until admin verification.

---

# Doctor Registration Rules

If the selected role is:

```text
DOCTOR
```

require:

```text
BM&DC Registration Number
Medical Facility Name
Designation
Additional Information
```

BM&DC Registration Number must be globally unique according to the schema.

The additional-information field must support a large text value.

---

# Other Professional Registration Rules

For non-doctor roles require:

```text
Medical Facility Name
Designation
Additional Information
```

Do not require BM&DC information unless explicitly required by the supplied documentation.

---

# Existing Citizen Becoming a Professional

If a professional registration uses an NID already belonging to an existing HealthLink citizen account:

```text
do not create another user
```

Require the existing account to authenticate and use the professional onboarding flow.

Preserve one identity per person.

---

# Admin Rules

Admins use a separate:

```text
/admin/login
```

interface.

Admin accounts are trusted operational accounts.

Do not provide public admin registration.

Admin responsibilities through Phase 14 include:

```text
professional verification
professional rejection
facility matching/creation
citizen NID/BCN identity support
admin audit records
```

Professional verification must be role-specific.

A doctor verification page must expose the required BM&DC information.

Rejection requires a reason.

Verification/rejection actions must be audited.

---

# Professional Login Rules

Professional login requires:

```text
NID
Password
Professional Role dropdown
```

The selected role defines the active professional role context.

A professional session must not merely say:

```text
user is healthcare professional
```

It must identify which verified:

```text
professional_role_registration
```

is active.

If a multi-role user logs in as:

```text
LAB_TECHNICIAN
```

they must not be allowed to call doctor-only endpoints, even if they also possess a verified DOCTOR role.

---

# Portal Isolation

Maintain three separate portal contexts:

```text
CITIZEN
PROFESSIONAL
ADMIN
```

Backend APIs must enforce portal context.

Frontend route guards are only a usability mechanism.

They are not authoritative security.

---

# Doctor Search Requirements

By Phase 9, citizens must be able to search VERIFIED doctors using:

```text
doctor name
hospital / medical facility name
```

Only verified doctor-role registrations are searchable/bookable.

Do not expose:

```text
NID
admin verification internals
sensitive identity data
```

---

# Doctor Practice Schedule Requirements

Doctors configure:

```text
practice weekdays
start time
end time
maximum patients per day
```

Use the doctor practice schedule model defined in V6.

The schedule is associated with the verified doctor role context.

Only VERIFIED DOCTOR roles may manage doctor practice schedules.

---

# Appointment Model

HealthLink uses a **serial-based chamber appointment model**.

It is not a fixed consultation-time-slot system.

A citizen:

```text
finds doctor
selects an allowed practice date
books appointment
receives serial number
```

The booking must check:

```text
selected weekday is practiced
schedule is active
daily active appointment count < max_patients
```

---

# Serial Assignment

Use:

```text
new serial = MAX(existing serial_number) + 1
```

for that:

```text
doctor role
facility
appointment date
```

Example:

```text
issued serials = 1,2,3,4,5

serial 3 cancels

next booking = serial 6
```

Never renumber serials.

Never reuse cancelled serial numbers.

---

# Daily Capacity

Daily capacity is based on active bookings, not maximum serial.

Example:

```text
max patients = 5
serials 1–5 issued
serial 3 cancels

active appointments = 4

another booking is allowed
new serial = 6
```

---

# Appointment Booking Concurrency

Appointment serial creation must be transaction-safe.

Do not:

```text
SELECT MAX()
then later INSERT
```

without protecting concurrent requests.

Follow the V6 recommendation for a PostgreSQL transaction-scoped lock or an equivalent safe implementation.

Inside the protected transaction:

```text
load practice configuration
count active appointments
verify capacity
calculate MAX(serial)
create appointment
create/get practice session
create WAITING queue entry
commit
```

Preserve the unique serial constraint as final protection.

---

# Appointment History vs Serial Queue

Do not hard-delete appointment history when a citizen cancels, is skipped, removed, or marked absent.

Maintain separate concepts:

```text
appointments
appointment_queue_entries
doctor_practice_sessions
```

The appointment is the historical booking.

The queue entry is the operational chamber status.

---

# Queue States

Implement the statuses defined by V6:

```text
WAITING
CURRENT
SKIPPED
DONE
REMOVED
CANCELLED
```

Only one queue entry may be:

```text
CURRENT
```

for one practice session.

Implement the database-level partial unique constraint/index described in V6.

---

# Starting Doctor Practice

When the doctor starts today's chamber:

```text
verify active role is VERIFIED DOCTOR
load/create today's practice session
set session ACTIVE
select lowest WAITING serial
change it to CURRENT
```

If there are no waiting patients, there is no current patient.

---

# Queue Advancement

Centralize queue advancement in one service/helper.

The next patient is always:

```text
lowest serial
WHERE queue status = WAITING
```

Skip:

```text
CURRENT → SKIPPED
advance queue
```

Remove:

```text
queue → REMOVED
appointment → REMOVED_BY_DOCTOR
advance if necessary
```

No-show:

```text
appointment → NO_SHOW
queue → REMOVED
advance if necessary
```

Citizen cancellation:

```text
appointment → CANCELLED
queue → CANCELLED
```

Cancelled/removed/skipped/done rows are ignored when selecting the next active serial.

---

# Current Patient Access

This is a critical security boundary.

Before a patient becomes CURRENT, the doctor may see only limited queue information such as:

```text
display name
serial
appointment reason
```

The doctor must **not** automatically receive full medical-record access to every person booked that day.

Full appointment-derived access activates only when:

```text
professional portal session
+
active role is VERIFIED DOCTOR
+
doctor owns active practice session
+
queue entry is CURRENT
+
appointment belongs to that doctor role
```

Then the doctor may access the current patient's available medical/profile information required by Phase 12.

---

# Consultation Workspace

Phase 12 must deliver a real doctor consultation workspace.

It should combine current-patient information with the visit form.

Conceptually:

```text
Current Serial
Patient

Profile / Existing Clinical Information

Clinical Notes
Diagnosis / Visit Information
Follow-up Information

Prescription area introduced in Phase 13
```

Build the UI for efficient chamber use.

Do not expose waiting patients' full records.

---

# Medical Visit Rules

A chamber consultation creates a structured medical visit.

The visit is linked to:

```text
citizen
doctor role registration
facility
appointment
```

During consultation it may remain:

```text
DRAFT
```

When the appointment finishes in Phase 14:

```text
visit → FINALIZED
```

---

# Prescription Requirements

Phase 13 must implement the actual chamber prescription workflow.

Prescription structured fields include:

```text
multiple medicine entries
diagnostic information
medical advice
notes
```

Medicine rows include:

```text
medicine name
dosage
frequency
duration
instructions
```

Frontend must support:

```text
+ Add Medicine
Remove Medicine
```

Do not store the entire prescription only as a PDF.

Structured database data is the source of truth.

---

# Prescription PDF

When the doctor saves a prescription:

```text
save structured prescription
save medicine rows
generate electronic PDF
store PDF privately
link prescription to generated document
```

The PDF should include relevant doctor/patient/visit/prescription information defined in V6.

Do not print NID or BCN by default.

If PDF generation fails:

```text
do not discard already committed structured medical data
```

Handle PDF generation failure explicitly and allow regeneration/retry.

---

# Prescription Authorization

Citizen:

```text
can read own prescription
can view/download own PDF
cannot edit
```

Author doctor:

```text
can read
can edit
can regenerate PDF
```

Other doctors:

```text
cannot edit
```

even if they can otherwise read the record.

The author check must compare the active doctor role registration against:

```text
author_doctor_role_registration_id
```

not merely the base user ID.

---

# Author Prescription Editing

Author doctor may edit the prescription even after appointment completion.

On edit:

```text
update structured prescription
update medicine items
regenerate PDF
audit the change when audit infrastructure exists
```

Do not make prescriptions globally immutable in a way that violates this requirement.

---

# Finishing Appointment

Phase 14 implements:

```text
POST finish appointment
```

Required conditions include:

```text
appointment is the current queue appointment
active doctor role owns it
medical visit exists
```

Prescription is not mandatory because a medical consultation may legitimately have no medicine prescribed.

On finish:

```text
finalize visit
appointment → COMPLETED
queue → DONE
automatically select next lowest WAITING serial
next serial → CURRENT
```

The UI should naturally move the doctor to the next patient.

---

# Payment

Do not implement payment.

Chamber payment is offline.

No payment table, payment gateway, billing state, or payment API is needed through Phase 14.

The doctor manually presses Finish Appointment after completing the consultation and handling offline payment.

---

# Security Requirements Through Phase 14

At minimum test:

```text
Citizen A cannot access Citizen B's private resources.

Citizen token cannot call admin endpoints.

Citizen token cannot call professional endpoints.

Professional token cannot call admin endpoints.

Pending/rejected professional has no clinical capabilities.

LAB_TECHNICIAN active role cannot perform DOCTOR actions.

Unverified DOCTOR cannot create practice schedule.

Another doctor cannot manipulate a doctor's queue.

Doctor cannot view full waiting-patient record.

Doctor can view full CURRENT patient record.

Citizen cannot edit prescription.

Non-author doctor cannot edit prescription.

Author doctor can edit prescription.

Only correct citizen can download own prescription PDF.

Wrong object IDs do not bypass authorization.
```

---

# Sensitive Data Rules

Do not log:

```text
passwords
raw refresh tokens
JWT secrets
full NID unnecessarily
full BCN unnecessarily
DATABASE_URL credentials
OpenAI key
```

Mask identity values in administrative UIs when practical.

Never put NID/BCN in JWT payloads.

---

# Git and Secret Rules

Maintain a proper `.gitignore`.

Never commit:

```text
.env
backend/.env
frontend/.env.local
Neon connection URL
JWT secret
private prescription PDFs
future OpenAI key
```

Before phase commits inspect:

```bash
git status
git diff
```

---

# Required Testing Strategy

For every phase, implement appropriate automated tests.

At minimum include:

```text
happy path
validation failure
authentication failure
authorization failure
important uniqueness conflict
important state conflict
```

For security-sensitive features, explicitly test cross-user and cross-role attempts.

Use a PostgreSQL-compatible test setup where database-specific behavior is important, especially for:

```text
constraints
partial unique indexes
serial concurrency
transactions
```

---

# Phase Completion Checklist

Do not mark a phase complete unless every applicable item is done.

## Database

```text
ORM implemented
constraints implemented
indexes implemented
migration generated
migration reviewed
migration applies successfully
```

## Backend

```text
Pydantic schemas
repository
service
routes
authentication
authorization
business rules
error handling
tests
```

## Frontend

```text
TypeScript types
API client integration
actual TSX page/component
form validation
loading state
error state
empty state where applicable
success feedback
responsive behavior
modern polished styling
consistent premium HealthLink design language
```

## Dependency Manifests

```text
backend/requirements.txt updated if Python dependencies changed
frontend/package.json and lockfile updated if frontend dependencies changed
no per-flow or per-phase dependency manifests created
```

## Integration

```text
frontend talks to real FastAPI endpoint
backend talks to real PostgreSQL schema
no temporary mock remains
browser workflow works
```

## Documentation

Update relevant project documentation after each completed phase.

---

# Working Procedure

Execute the phases sequentially.

For each phase:

```text
1. Read the exact phase requirements from V6.
2. Cross-check conceptual rules in the System Context document.
3. Inspect existing repository state.
4. Produce a concise implementation checklist.
5. Implement database and migration.
6. Implement backend.
7. Run backend tests.
8. Implement frontend.
9. Integrate real API.
10. Test normal browser flow.
11. Test authorization/edge cases.
12. Review frontend quality, responsiveness, and usability.
13. Update documentation.
14. Review git diff/status.
15. Report what was completed.
16. Move to the next phase only if the current phase is working.
```

Do not skip directly to later phases.

---

# Progress Reporting

After each phase, report:

```text
Phase completed
Files/modules added or materially changed
Database migration created
API endpoints implemented
Frontend pages implemented
Tests added
Tests passing/failing
Any documented limitation
Next phase
```

Do not claim a phase is complete when significant required functionality remains.

If a test fails, report the failure and fix it before proceeding whenever possible.

---

# Handling Ambiguity

The two supplied Markdown documents intentionally define Phases 0–14 in substantial detail.

Do not invent new product behavior when the documents already define the requirement.

If a minor implementation detail is not explicitly specified:

```text
choose the simplest practical solution
that preserves the documented architecture and invariants
```

Document the assumption.

Do not use ambiguity as a reason to redesign major workflows.

Do not add future-scope functionality just to make the architecture "more complete."

---

# Final Target State

When you stop after Phase 14, the system should support this complete flow:

```text
Citizen registers using NID or BCN
        ↓
Citizen logs in
        ↓
BCN citizen may later add NID once
        ↓
Professional registers using NID
        ↓
Professional selects role
        ↓
Doctor submits BM&DC + facility/designation/info
        ↓
Admin logs in
        ↓
Admin verifies doctor/facility
        ↓
Doctor logs in using NID + password + DOCTOR
        ↓
Doctor configures practice weekdays/time/max patients
        ↓
Citizen searches doctor by doctor name or hospital/facility
        ↓
Citizen chooses practice date
        ↓
Appointment booked
        ↓
MAX+1 serial assigned
        ↓
Doctor starts daily chamber session
        ↓
Lowest active serial becomes CURRENT
        ↓
Doctor receives current-patient clinical access
        ↓
Doctor records consultation
        ↓
Doctor adds medicines using dynamic prescription form
        ↓
Doctor adds diagnostic information
        ↓
Doctor adds medical advice
        ↓
Structured prescription saved
        ↓
Electronic prescription PDF generated
        ↓
Citizen can view/download own prescription
        ↓
Only author doctor may edit prescription
        ↓
Doctor finishes appointment
        ↓
Visit finalized
        ↓
Queue marks appointment DONE
        ↓
Next lowest WAITING serial becomes CURRENT
```

This is the required implementation boundary.

Once Phase 14 has passed all applicable tests and acceptance criteria, **STOP**.

Do not begin Phase 15 until I provide explicit instructions.
