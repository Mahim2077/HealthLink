# HealthLink — System Context and Developer Documentation

> **Document type:** System context + developer documentation  
> **Purpose:** Give developers, reviewers, and coding agents a complete written understanding of HealthLink without needing to read the earlier iterative design conversations.  
> **Authoritative implementation baseline:** `HealthLink_Synchronized_System_Database_Implementation_Plan_V6.md`

---

# 1. What HealthLink Is

HealthLink is a healthcare information platform designed around a centralized electronic medical record.

Its purpose is to allow a citizen's medical information to remain available across healthcare interactions instead of being fragmented between clinics, hospitals, diagnostic centers, and paper documents.

The system is designed around three distinct user experiences:

```text
Citizen Portal
Professional Portal
Admin Portal
```

The platform supports:

```text
Citizen identity and medical profile
Healthcare professional registration and verification
Doctor discovery
Doctor practice scheduling
Serial-based appointment booking
Daily chamber serial queues
Clinical consultations
Electronic prescriptions
Prescription PDF generation
Diagnostic test requests
Laboratory reports
Emergency medical information
Medicine reminders
Appointment reminders
Medical record access logging
AI-based explanations and summaries
```

The project deliberately avoids becoming a complete hospital-management platform.

It does not include online billing, insurance, telemedicine, pharmacy inventory, hospital accounting, or government interoperability in the initial architecture.

---

# 2. Architectural Style

HealthLink is a modular monolith.

The system consists of:

```text
Next.js frontend
        ↓
FastAPI REST backend
        ↓
Service layer
        ↓
Repository layer
        ↓
SQLAlchemy ORM
        ↓
Neon PostgreSQL
```

AI features communicate from the backend to OpenAI.

```text
Next.js
   ↓
FastAPI
   ↓
Authorization + data minimization
   ↓
OpenAI API
```

There are no microservices in the core project.

This decision keeps deployment, debugging, database transactions, authentication, and feature development practical for a student software-development project while still preserving clean module boundaries.

---

# 3. Technology Stack

## Frontend

```text
Next.js
TypeScript
TSX
Tailwind CSS
App Router
```

## Backend

```text
Python
FastAPI
fastapi[standard]
SQLAlchemy ORM
Pydantic
Pydantic Settings
Alembic
JWT authentication
```

## Database

```text
PostgreSQL
Neon hosted PostgreSQL
```

## AI

```text
OpenAI API
```

## Source Control / Development

```text
Git
GitHub
VS Code
Postman or equivalent API testing client
```

---


# 3A. Dependency Management

HealthLink is a modular monolith, so dependency management is centralized rather than split by workflow.

The backend has one authoritative Python dependency manifest:

```text
backend/requirements.txt
```

All backend flows—authentication, citizen, professional, admin, appointments, chamber, prescriptions, diagnostics, reminders, audit, and AI—share this backend environment.

Do not create a separate `requirements.txt` for each flow or phase.

When a backend feature introduces a new third-party Python package, the same phase must update `backend/requirements.txt`.

The frontend similarly has one authoritative dependency manifest:

```text
frontend/package.json
```

Citizen, Professional, and Admin portals are parts of the same Next.js application and therefore share the same `package.json` and package-manager lockfile.

In practical terms:

```text
backend/requirements.txt
    = Python dependency source of truth

frontend/package.json
    = frontend dependency source of truth
```

A dependency should never exist only because it happens to be installed on one developer's machine.

The dependency manifests must be sufficient to recreate the application's required environment.

---

# 4. Repository Philosophy

The project should be organized by modules and features rather than placing all logic into a few large files.

Backend modules include:

```text
auth
identity
citizens
professionals
admin
facilities
doctors
appointments
chamber
access
medical_records
prescriptions
diagnostics
reminders
emergency
audit
ai
```

A backend feature generally follows:

```text
models
schemas
repository
service
routes
tests
```

The expected request flow is:

```text
FastAPI Route
    ↓
Service
    ↓
Repository
    ↓
SQLAlchemy
    ↓
PostgreSQL
```

Routes should remain thin.

Business rules should live in services.

Database access should be encapsulated through repository code where practical.

---

# 5. Core Identity Philosophy

HealthLink uses one base user identity.

The system does not create completely separate authentication databases for citizens, professionals, and administrators.

The base relationship is:

```text
users
│
├── citizen capability
│
├── healthcare professional capability
└── admin capability
```

A normal person can be both:

```text
Citizen
+
Healthcare Professional
```

using the same underlying user identity.

However, the application still presents separate portals and login interfaces because each portal has different responsibilities and authorization logic.

---

# 6. Login Interfaces

HealthLink has three login pages:

```text
/citizen/login
/professional/login
/admin/login
```

## Citizen Login

Credentials:

```text
Email
Password
```

A valid citizen login requires:

```text
valid user
+
citizen profile exists
```

## Professional Login

Credentials:

```text
NID
Password
Professional Role
```

Example:

```text
NID: 1234567890
Password: ********
Role: DOCTOR
```

The selected role determines the active professional context.

## Admin Login

Credentials:

```text
Email
Password
```

An admin account must already exist as a trusted administrative account.

Admins cannot register themselves through a public form.

---

# 7. Citizen Identity

A citizen may register using either:

```text
National ID
OR
Birth Certificate Number
```

Initial registration allows exactly one.

Examples:

```text
NID present, BCN absent       valid

NID absent, BCN present       valid

NID absent, BCN absent        invalid

NID present, BCN present      invalid during initial registration
```

The citizen identity model exists so younger citizens or citizens who do not yet have an NID can still create an account.

---

# 8. National ID Storage

NID is centralized.

It is stored in one authoritative table:

```text
user_national_identifiers
```

This is important because the same user may later become a healthcare professional.

The system must never create one citizen NID record and another unrelated professional NID record for the same person.

NID is globally unique.

---

# 9. Birth Certificate Number

Birth Certificate Number is citizen-only.

Professionals do not register professionally using BCN.

BCN is globally unique among citizen identities.

Healthcare professional registration always requires NID.

---

# 10. BCN to NID Upgrade

A citizen who originally registered using Birth Certificate Number may later add an NID.

This is a one-time self-service action.

Frontend workflow:

```text
Enter new NID

Type:

CONFIRM

Submit
```

Backend requirements:

```text
citizen currently has BCN

citizen currently has no NID

submitted NID is globally unique

confirmation equals exactly CONFIRM
```

After success:

```text
BCN remains stored
NID is added
citizen cannot self-replace the NID later
```

If a mistake occurs after this operation, the citizen must contact an administrator.

---

# 11. Healthcare Professional Accounts

Healthcare professional capability is attached to an existing or newly created base user.

A professional has:

```text
healthcare_professional_profile
```

and one or more:

```text
professional_role_registrations
```

Professional roles are separate because one healthcare professional may theoretically hold more than one professional role.

---

# 12. Professional Roles

The role catalog includes:

```text
DOCTOR
LAB_TECHNICIAN
NURSE
PHARMACIST
RADIOLOGY_TECHNICIAN
OTHER_HEALTHCARE_PROFESSIONAL
```

Not every role has full functionality in the initial product.

The presence of a role does not automatically grant every healthcare action.

Permissions are based on explicit capability rules.

---

# 13. Doctor Registration

A professional who selects:

```text
DOCTOR
```

must provide:

```text
NID
Name
Email
Password
BM&DC Registration Number
Medical Facility Name
Designation
Additional Information
```

The additional-information field is intended to hold a relatively large amount of text.

---

# 14. Other Professional Registration

A non-doctor professional provides:

```text
NID
Name
Email
Password
Professional Role
Medical Facility Name
Designation
Additional Information
```

They do not provide a BM&DC registration number unless a future role-specific rule requires one.

---

# 15. Professional Verification

Professional registration does not immediately grant professional access to medical workflows.

Every professional role begins as:

```text
PENDING
```

An administrator reviews the registration.

Possible outcomes:

```text
PENDING
VERIFIED
REJECTED
```

Only:

```text
VERIFIED
```

professional roles may perform their allowed clinical workflows.

A professional can sign in while pending or rejected, but their portal is limited to verification-status information.

---

# 16. Why Professional Role Context Matters

A professional session is not identified only by the user.

It is identified by:

```text
user
+
selected verified professional role
```

Example:

A person who has:

```text
DOCTOR
LAB_TECHNICIAN
```

must explicitly select which role they are using during professional login.

This selected role becomes the active professional role context.

Clinical authorization checks the active role.

A lab-technician login must not be able to use doctor endpoints even if the same person also has a doctor role.

---

# 17. Admin Responsibilities

The admin portal is intentionally focused.

Admin responsibilities include:

```text
Professional verification
Facility registration / matching
Citizen identity support
Administrative audit review
```

The admin portal does not initially provide:

```text
billing administration
insurance administration
government analytics
financial reports
```

---

# 18. Healthcare Facilities

Professional registrations contain the facility name entered by the professional.

During admin verification, the administrator:

```text
matches the submitted facility to an existing facility
OR
creates the facility in HealthLink
```

A verified professional role therefore becomes linked to a registered facility.

Facilities include:

```text
Hospital
Clinic
Diagnostic Center
Pharmacy
```

Only the facilities needed by implemented workflows need active application functionality.

---

# 19. Doctor Discovery

Citizens can search for doctors.

Primary search fields:

```text
Doctor name
Hospital / medical facility name
```

The search returns only verified doctors.

The citizen can view information such as:

```text
doctor name
facility
designation
practice schedule
```

NID and administrative verification information are never exposed.

---

# 20. Doctor Practice Schedule

Doctors control their own chamber schedule.

They configure:

```text
which weekdays they practice

practice start time

practice end time

maximum number of patients per day
```

Example:

```text
Sunday
4:00 PM – 9:00 PM
Maximum patients: 30

Tuesday
4:00 PM – 9:00 PM
Maximum patients: 30
```

The initial architecture assumes one practice period for a doctor on a given weekday.

---

# 21. Appointment Model

HealthLink appointments are serial-based.

They are not fixed-time-slot appointments.

The citizen chooses:

```text
doctor
practice date
```

The system verifies:

```text
doctor practices on that weekday

daily active booking count is below maximum
```

If booking succeeds, the citizen receives a serial number.

---

# 22. Serial Number Rule

Serial numbers use a MAX approach.

```text
new serial = maximum previously issued serial + 1
```

Example:

```text
Existing:
1
2
3
4
5

Serial 3 cancels.

Next new patient gets:

6
```

Serial number 3 is not reused.

Serial numbers are historical identifiers for that doctor/date.

---

# 23. Daily Capacity Rule

Daily capacity is not calculated from the largest serial number.

It is based on active appointments.

Example:

```text
Maximum patients = 5

Issued serials:
1
2
3
4
5

Serial 3 cancels.

Active patients = 4

A new patient may book.

New serial = 6
```

This separates:

```text
serial identity
```

from:

```text
daily active capacity
```

---

# 24. Appointment History vs Queue State

HealthLink does not hard-delete appointment history when a patient cancels or is removed.

The system keeps:

```text
appointments
```

and separately:

```text
appointment_queue_entries
```

This distinction is important.

The appointment represents the historical booking.

The queue entry represents today's chamber state.

---

# 25. Daily Practice Session

Each doctor's chamber day is represented by:

```text
doctor_practice_session
```

Example:

```text
Doctor: Dr. Rahman
Facility: Example Hospital
Date: 2026-08-15
Status: ACTIVE
```

A practice session may have multiple queue entries.

Only one queue entry may be:

```text
CURRENT
```

at a time.

---

# 26. Queue States

Queue states:

```text
WAITING
CURRENT
SKIPPED
DONE
REMOVED
CANCELLED
```

Meaning:

## WAITING

Patient has a valid booking and is waiting.

## CURRENT

Doctor is currently consulting this patient.

## SKIPPED

Patient was absent when called, but may potentially be handled later.

## DONE

Consultation completed.

## REMOVED

Doctor removed the patient from today's active serial.

## CANCELLED

Citizen cancelled the appointment.

---

# 27. Queue Advancement

When the doctor starts practice, HealthLink selects:

```text
lowest serial number
with queue status WAITING
```

and changes it to:

```text
CURRENT
```

When the current patient is:

```text
finished
skipped
removed
marked no-show
```

the system automatically selects the next lowest `WAITING` serial.

Cancelled serials are automatically ignored.

---

# 28. Citizen Appointment Cancellation

If the citizen cancels before their consultation begins:

```text
appointment → CANCELLED

queue entry → CANCELLED
```

The serial disappears from the active pool.

The original appointment remains in the database.

Cancellation also frees a place in the doctor's daily capacity.

---

# 29. Current Patient Security Boundary

One of the most important security rules in HealthLink is:

```text
a doctor does not automatically receive full medical-record access
to every person booked that day
```

Before the patient's turn, the doctor sees only limited queue information:

```text
patient display name
serial
appointment reason
```

Full medical access becomes available when:

```text
practice session is ACTIVE

queue entry is CURRENT

active doctor role owns the session
```

---

# 30. Current Patient Information

During the current consultation, the doctor may view:

```text
patient profile
medical history
previous visits
previous prescriptions
lab reports
emergency profile
```

This allows the doctor to make the current consultation informed by previous medical information.

Sensitive record access is audit logged.

---

# 31. Consultation Workspace

The doctor receives a unified consultation screen.

Conceptually:

```text
Current Serial
Patient Name

Patient Information
-------------------
Profile
Emergency Information
Medical History
Previous Prescriptions
Lab Reports

Consultation
------------
Clinical Notes
Diagnosis
Follow-up Information

Prescription
------------
Medicines
Diagnostics Information
Medical Advice
Notes

Finish Appointment
```

The UI should make this workflow efficient because this is the central doctor-facing page.

---

# 32. Medical Visit

Every successful chamber consultation creates a:

```text
medical_visit
```

A medical visit stores information such as:

```text
citizen
doctor role
facility
appointment
visit date
chief complaint
clinical notes
diagnosis
follow-up instructions
status
```

The visit begins as:

```text
DRAFT
```

and is finalized when the appointment is finished.

---

# 33. Prescription Workflow

The doctor can create a structured prescription.

The prescription includes:

```text
multiple medicine rows
diagnostic information
medical advice
notes
```

Medicine rows support dynamic addition.

Example:

```text
Medicine 1
---------
Medicine Name
Dosage
Frequency
Duration
Instructions

[ + Add Medicine ]

Medicine 2
---------
...
```

---

# 34. Free-Text Diagnostics vs Structured Diagnostic Tests

HealthLink supports two related concepts.

## Prescription Diagnostic Information

A doctor may write general diagnostic instructions directly in the prescription.

Example:

```text
CBC
Serum Creatinine
Chest X-Ray
```

This appears in the prescription and its PDF.

## Structured Diagnostic Test

The doctor may also create an actual structured diagnostic-test request in the diagnostic workflow.

These two concepts can coexist.

The free-text section is convenient for the prescription.

The structured request is needed when the test is tracked through HealthLink and assigned to diagnostic staff.

---

# 35. Medical Advice

The prescription also includes:

```text
medical_advice
```

Example:

```text
Drink adequate water.
Avoid strenuous exercise for three days.
Return after one week.
```

This appears in the electronic prescription PDF.

---

# 36. Electronic Prescription PDF

The structured prescription stored in PostgreSQL is the authoritative record.

The PDF is a generated representation.

Flow:

```text
Doctor saves prescription
        ↓
Structured data stored
        ↓
HealthLink generates PDF
        ↓
PDF stored privately
        ↓
Citizen can view/download PDF
```

If PDF generation fails, the structured prescription should remain saved.

The system can retry PDF generation.

---

# 37. Prescription PDF Content

Recommended fields:

```text
HealthLink

Doctor Name
BM&DC Registration Number
Designation
Medical Facility
Visit Date

Patient Name
Age or Date of Birth
Serial Number

Medicine Table

Diagnostic Information

Medical Advice

Additional Notes
```

NID and BCN should not be printed by default.

---

# 38. Prescription Editing

The citizen cannot edit a prescription.

Only the author doctor may edit their prescription.

The author is identified by:

```text
author_doctor_role_registration_id
```

When the author edits the prescription:

```text
structured prescription is updated
medicine rows are updated
PDF is regenerated
audit entry is written
```

Other doctors can never edit another doctor's prescription.

They may only read it if independently authorized to access the patient record.

---

# 39. Finishing an Appointment

The doctor finishes the appointment after the chamber consultation is complete.

Payment is handled offline and is not represented in HealthLink.

When the doctor presses:

```text
Finish Appointment
```

the backend:

```text
finalizes the medical visit

marks appointment COMPLETED

marks queue entry DONE

selects the next WAITING serial

makes that serial CURRENT
```

The next patient therefore appears naturally.

---

# 40. Offline Payment

HealthLink does not process chamber payment.

No payment table is required.

No payment gateway is required.

The doctor handles payment outside the application.

The doctor simply finishes the appointment after completing the consultation and any offline payment process.

---

# 41. Medical History

HealthLink does not store a duplicate "medical history" table.

Medical history is derived from actual records:

```text
medical visits
prescriptions
diagnostic tests
lab reports
```

The citizen sees these as a chronological timeline.

This avoids duplicated, inconsistent medical-history data.

---

# 42. Diagnostic Test Workflow

A verified doctor may create a structured diagnostic request.

The request may be assigned to a verified diagnostic professional, initially:

```text
LAB_TECHNICIAN
```

The request has statuses such as:

```text
REQUESTED
IN_PROGRESS
COMPLETED
CANCELLED
```

---

# 43. Lab Technician Workflow

A lab technician logs in through the same professional login interface:

```text
NID
Password
Role = LAB_TECHNICIAN
```

The lab technician sees diagnostic tests assigned to their role.

They can:

```text
view assigned tests
mark work in progress
create lab report
edit draft report
finalize report
```

They do not receive doctor capabilities.

---

# 44. Laboratory Reports

Lab reports are structured.

Each report may contain multiple items:

```text
Parameter Name
Result Text
Numeric Result
Unit
Reference Range
Flag
```

The system stores both:

```text
result_value_text
```

and optionally:

```text
result_value_numeric
```

because medical results are not always purely numeric.

Examples:

```text
Negative
Positive
<5
Not Detected
7.2
```

---

# 45. Lab Trends

Numeric lab values can be queried over time.

Lab trends are derived from historical structured report items.

There is no separate lab-trend table.

This reduces duplicate data.

---

# 46. Emergency Medical Profile

Every citizen may maintain a concise emergency profile.

Fields include:

```text
allergies
chronic conditions
current medications
emergency contact
special notes
```

Blood group is read from the citizen profile instead of duplicating it.

During a current doctor consultation, the doctor can view the emergency profile.

---

# 47. Medicine Reminders

Citizens can create reminders from prescription medicines or manually.

A reminder contains:

```text
medicine
start date
end date
timezone
one or more daily reminder times
```

The architecture supports multiple reminder times per day.

---

# 48. Appointment Reminders

Appointment reminders are generated from:

```text
appointment date
doctor practice schedule
```

Because appointments are serial-based rather than fixed-time-slot appointments, the reminder should communicate the appointment date and relevant doctor/chamber information rather than pretending the patient has a guaranteed exact consultation time.

---

# 49. Notification System

HealthLink initially uses in-app notifications.

Notification examples:

```text
Medicine Reminder
Appointment Reminder
```

Actions may include:

```text
Read
Snooze
Taken
Dismiss
```

No SMS, email, or push-notification infrastructure is required initially.

---

# 50. Manual Patient Access Grants

The active chamber queue gives the current doctor temporary contextual access.

Separately, the citizen may optionally grant a professional access outside that current appointment.

Possible scopes:

```text
FULL_MEDICAL_HISTORY
VISITS_ONLY
PRESCRIPTIONS_ONLY
LAB_REPORTS_ONLY
EMERGENCY_PROFILE_ONLY
```

Citizens may revoke such manual grants.

Appointment-derived access should not create a permanent grant.

---

# 51. Record Access Logging

HealthLink records sensitive medical access.

The audit system should answer:

```text
Who accessed the patient?
Under which professional role?
At which facility?
Which type of record?
What action?
When?
```

Examples:

```text
VIEW medical history
VIEW prescription
VIEW lab report
UPDATE author's prescription
VIEW emergency profile
AI_ACCESS medical context
```

Audit logs are append-oriented.

Normal application users do not edit or delete them.

---

# 52. Citizen Access Transparency

Citizens can see a simplified access-history page.

It may display:

```text
professional name
professional role
facility
record category
action
date/time
```

It should not expose internal request IDs or implementation metadata.

---

# 53. AI Features

HealthLink contains five major AI features:

```text
Symptom Guidance
Prescription Explanation
Lab Report Explanation
Medical History Summary
Healthcare Chatbot
```

AI is an explanatory assistant.

It is not the authoritative medical record.

---

# 54. AI Prescription Explanation

A citizen can ask HealthLink to explain a stored prescription.

The backend sends only the necessary prescription data.

The AI can explain:

```text
what each medicine instruction means
dosage/frequency wording
general medication-related instructions
medical advice written in the prescription
```

It must not invent a new prescription.

---

# 55. AI Lab Report Explanation

HealthLink can explain structured lab values.

The AI receives:

```text
parameter
value
unit
reference range
flag
relevant summary
```

It provides educational explanation rather than a medical diagnosis.

---

# 56. AI Medical History Summary

HealthLink can summarize a long medical history.

The summary is derived from real HealthLink records.

Recommended sections:

```text
Key Medical Events
Recorded Diagnoses
Recent Prescriptions
Recent Lab Findings
Follow-up Notes
```

Where possible, summary sections should reference source records.

---

# 57. AI Healthcare Chatbot

Two conceptual modes are supported:

```text
GENERAL
RECORD_AWARE
```

## GENERAL

Does not automatically load medical records.

## RECORD_AWARE

The citizen explicitly selects medical context.

Examples:

```text
Ask about this prescription
Ask about this lab report
Ask about my medical summary
```

---

# 58. AI Symptom Guidance

Symptom guidance is explicitly non-diagnostic.

The output can contain:

```text
summary
general information
red flags
suggested next step
disclaimer
```

It must avoid acting as a replacement for a clinician.

---

# 59. AI Privacy Rules

The backend must minimize medical context sent to OpenAI.

Do not send:

```text
NID
BCN
home address
unrelated medical records
```

unless an explicit future requirement makes it necessary.

AI calls involving medical records should also be audited.

---

# 60. Clinical Data Authority

The official medical record consists of structured database records.

Examples:

```text
medical visit
prescription
diagnostic request
lab report
emergency profile
```

AI-generated text never directly replaces these records.

AI cannot automatically:

```text
diagnose
prescribe
modify prescription
modify lab values
finalize a visit
complete an appointment
```

---

# 61. Record Finalization

Medical visits and lab reports use:

```text
DRAFT
FINALIZED
```

Normal edits are blocked after finalization.

Prescription editing is a deliberate exception:

```text
author doctor can edit their own prescription later
```

Such edits must be audited and regenerate the prescription PDF.

---

# 62. Data Deletion Philosophy

Medical and identity history should not be casually deleted.

Use deactivation for accounts where possible.

Clinical foreign keys generally use restrictive deletion behavior.

Safe child data may cascade only when appropriate.

Examples of reasonable child relationships:

```text
prescription → prescription items
lab report → lab report items
medicine reminder → reminder times
```

Appointments should not be deleted simply because the patient leaves the active queue.

---

# 63. Security Model

Authorization should conceptually follow:

```text
Authentication
    ↓
Portal
    ↓
Active Professional Role if applicable
    ↓
Professional Verification State
    ↓
Role Capability
    ↓
Patient / Resource Relationship
    ↓
Current Queue Context or Manual Grant
    ↓
Object-Level Authorization
    ↓
Audit
```

This chain is central to HealthLink security.

---

# 64. Important Security Examples

## Example 1

Citizen A changes a URL ID to Citizen B's prescription.

Expected:

```text
403 or 404
```

No data leak.

## Example 2

A lab technician attempts:

```text
POST /visits
```

Expected:

```text
403
```

## Example 3

A multi-role professional logs in as:

```text
LAB_TECHNICIAN
```

and tries to create a prescription.

Expected:

```text
403
```

Even if that same user also has a verified doctor role.

## Example 4

Doctor views tomorrow's waiting patient medical history before that patient becomes current.

Expected:

```text
denied
```

unless a separate manual patient access grant exists.

---

# 65. Authentication Tokens

Use JWT access tokens and revocable refresh sessions.

Recommended browser strategy:

```text
Access token:
    short-lived
    stored in memory

Refresh token:
    HttpOnly cookie
    stored hashed in database
```

Never store raw refresh tokens in PostgreSQL.

Avoid storing refresh tokens in `localStorage`.

---

# 66. Environment Secrets

The repository contains placeholders only.

Backend example:

```env
DATABASE_URL=

JWT_SECRET_KEY=

OPENAI_API_KEY=
```

Real values are configured locally or in deployment environments.

Never commit:

```text
Neon connection string
JWT secret
OpenAI key
production storage credentials
```

---

# 67. Prescription File Storage

Prescription PDFs are private medical documents.

In local development, HealthLink may use a private local-storage directory behind a storage abstraction.

In production, use protected persistent object storage.

The frontend should not receive raw public storage paths.

PDF access must go through an authorized backend flow or a short-lived protected download mechanism.

---

# 68. API Style

Base prefix:

```text
/api/v1
```

Common HTTP semantics:

```text
400 business-rule error
401 unauthenticated
403 unauthorized
404 not found
409 uniqueness or state conflict
422 validation error
500 server error
```

Standard simple error:

```json
{
  "detail": "Human-readable message"
}
```

---

# 69. Database Design Principles

Use:

```text
UUID primary keys
TIMESTAMPTZ timestamps
foreign keys
unique constraints
check constraints
indexes on common filters
```

Business logic should be enforced at multiple layers where appropriate:

```text
frontend validation
Pydantic validation
service rules
database constraints
```

The database acts as the final consistency boundary.

---

# 70. Important Database Invariants

```text
users.email unique

NID unique

BCN unique

one citizen profile per user

one professional base profile per user

one professional registration per role per professional

doctor BM&DC number unique

one doctor schedule per weekday

one serial number per doctor/facility/date

one queue entry per appointment

one CURRENT queue entry per practice session

one visit per appointment

one prescription per visit

one prescription PDF record per prescription

one lab report per structured diagnostic test

one emergency profile per citizen
```

---

# 71. Appointment Concurrency

Two users may attempt to book the final available appointment simultaneously.

The backend must not calculate serials only in application memory.

Booking should happen inside a transaction.

Use a doctor/date locking mechanism, such as a PostgreSQL transaction-scoped advisory lock.

Then:

```text
recount active appointments
check daily max
read MAX serial
insert appointment
insert queue entry
commit
```

The unique serial constraint is the final safety layer.

---

# 72. Why Queue Serial Is Not Duplicated

The serial number belongs to the appointment.

The queue entry links to the appointment.

Therefore the queue does not need its own independent serial-number column.

This prevents inconsistencies such as:

```text
appointment serial = 7
queue serial = 8
```

The queue always reads the serial from the appointment.

---

# 73. Why Medical History Is Derived

A separate medical-history table would duplicate information.

Instead:

```text
medical visits
prescriptions
diagnostics
lab reports
```

are queried into a combined timeline.

This makes the underlying clinical data authoritative and avoids synchronization problems.

---

# 74. Why Prescription Data Is Structured

The prescription PDF is convenient for humans, but the system should not depend on parsing PDFs.

Structured medicine rows make it possible to:

```text
display prescriptions cleanly
create medicine reminders
power AI explanations
search medicine history
regenerate PDFs
```

The PDF is therefore an output format, not the primary database representation.

---

# 75. Why Professional Actions Store Role Context

Clinical records should not reference only a generic healthcare-professional ID.

They store the professional-role registration responsible for the action.

This makes it possible to answer:

```text
Which user acted?

Which professional role were they using?

Which verified facility/designation context applied?
```

This is essential for multi-role professionals.

---

# 76. Why Admin Accounts Are Separate Operational Accounts

Admin functionality can modify high-risk identity and verification information.

The preferred architecture is for admins to use dedicated operational accounts instead of entering admin mode from an ordinary citizen/doctor portal.

This reduces accidental privilege mixing.

---

# 77. Primary Citizen Workflow

```text
Register with NID or BCN
        ↓
Login
        ↓
Maintain profile
        ↓
Search verified doctor
        ↓
View doctor practice days
        ↓
Book date
        ↓
Receive serial
        ↓
Attend chamber
        ↓
Doctor consults
        ↓
Visit stored
        ↓
Prescription generated
        ↓
PDF appears in profile
        ↓
Diagnostic reports may appear later
        ↓
Create medicine reminders
        ↓
Use AI explanations
        ↓
Review record access history
```

---

# 78. Primary Doctor Workflow

```text
Register with NID
        ↓
Select DOCTOR
        ↓
Provide BM&DC + Facility + Designation + Info
        ↓
Wait for Admin Verification
        ↓
Login with NID + Password + DOCTOR
        ↓
Configure practice weekdays/time/max patients
        ↓
Receive bookings
        ↓
Start chamber session
        ↓
Lowest serial becomes CURRENT
        ↓
Review current patient's information
        ↓
Consult patient
        ↓
Write prescription
        ↓
Generate PDF
        ↓
Finish appointment
        ↓
Next serial becomes CURRENT
```

---

# 79. Primary Lab Technician Workflow

```text
Register with NID
        ↓
Select LAB_TECHNICIAN
        ↓
Provide Facility + Designation + Info
        ↓
Admin verifies
        ↓
Login as LAB_TECHNICIAN
        ↓
View assigned diagnostic tests
        ↓
Create report
        ↓
Add report parameters
        ↓
Finalize report
        ↓
Citizen and authorized doctor can view
```

---

# 80. Primary Admin Workflow

```text
Login
    ↓
Review pending professional applications
    ↓
Inspect role-specific information
    ↓
Match/create facility
    ↓
Verify or reject
    ↓
Audit action stored
```

Identity-support workflow:

```text
Citizen reports NID/BCN problem
    ↓
Admin searches identity
    ↓
Reviews conflict
    ↓
Performs controlled correction
    ↓
Reason required
    ↓
Audit action stored
```

---

# 81. Development Method

HealthLink should be implemented using vertical slices.

A feature phase is not considered complete until it includes:

```text
database
migration
ORM
schemas
repository
service
route
frontend
authorization
tests
acceptance
```

This reduces the risk of building a large backend that has never been exercised by the actual UI.

---

# 82. Migration Policy

Every database schema modification is performed through Alembic.

Never manually change the Neon schema and then continue development without a migration.

Expected workflow:

```text
change ORM
generate migration
review migration
apply migration
run tests
```

---

# 83. Testing Priorities

Every feature should test at least:

```text
successful operation
invalid input
unauthenticated request
wrong portal
wrong role
wrong resource owner
important uniqueness/state conflict
```

Security-sensitive features require additional cross-patient tests.

---

# 84. High-Risk Areas Requiring Extra Tests

```text
BCN → NID one-time upgrade

professional verification

professional role login context

serial assignment concurrency

one CURRENT patient per chamber

current-patient medical access

author-only prescription editing

prescription PDF access

lab-technician role boundaries

admin identity corrections

medical access logs

AI record authorization
```

---

# 85. Features Intentionally Outside Scope

HealthLink does not initially include:

```text
online payments
insurance
billing
telemedicine
video consultation
pharmacy inventory
pharmacy dispensing
PACS
medical imaging storage
FHIR
HL7
government NID API
government analytics
doctor ratings
reviews
AI diagnosis
AI treatment decisions
AI prescription generation
```

These should not be added by implementation agents unless the project requirements change.

---

# 86. Terminology Reference

## User

Base authenticated identity.

## Citizen

A user with a citizen profile.

## Healthcare Professional

A user with a professional profile.

## Professional Role Registration

A professional's role-specific application and verification record.

## Active Professional Role

The professional role selected at login and used for authorization.

## Doctor Practice Schedule

Weekly recurring chamber configuration.

## Practice Session

One doctor's chamber session for one date.

## Appointment

Citizen's historical booking with doctor/date/serial.

## Queue Entry

Operational state of that appointment during the chamber session.

## Current Patient

The queue entry currently being consulted by the doctor.

## Medical Visit

Structured clinical consultation record.

## Prescription

Structured medicines/advice/diagnostic-information record linked to a visit.

## Prescription Document

Generated PDF representation of a prescription.

## Diagnostic Test

Structured request created by a doctor.

## Lab Report

Structured result associated with a diagnostic test.

## Manual Access Grant

Citizen-controlled permission allowing a professional to access selected medical information outside normal current-patient context.

---

# 87. Source-of-Truth Rules

Use the following hierarchy.

```text
Database structured medical data
    = authoritative clinical source

Generated PDF
    = human-readable representation

Medical history timeline
    = derived view

Lab trends
    = derived view

AI response
    = explanatory derived output

Frontend state
    = presentation only
```

Never reverse this hierarchy.

---

# 88. Developer Decision Checklist

Before implementing a feature, ask:

```text
Which portal owns the feature?

Which role can perform it?

Does it operate on citizen medical data?

What object-level authorization is required?

Does current chamber context matter?

Should the action be audited?

Which table is the source of truth?

Can a database constraint protect the invariant?

Does the frontend need a loading/error/empty state?

What happens if two requests occur concurrently?
```

---

# 89. Final Mental Model

The simplest way to understand HealthLink is:

```text
IDENTITY
    establishes who the person is

ROLE + ADMIN VERIFICATION
    establishes what a professional is allowed to do

DOCTOR SCHEDULE
    establishes when citizens may book

APPOINTMENT + SERIAL
    establishes the citizen's position in a chamber day

CURRENT QUEUE ENTRY
    establishes which patient the doctor may fully consult now

MEDICAL VISIT
    records the consultation

PRESCRIPTION / DIAGNOSTICS / LAB REPORTS
    record the clinical output

MEDICAL HISTORY
    combines those records over time

AUDIT
    records sensitive access

AI
    explains existing records without replacing them
```

---

# 90. Implementation Source of Truth

When implementing HealthLink, use the documents in this order:

```text
1. HealthLink_Synchronized_System_Database_Implementation_Plan_V6.md
   → authoritative database and phase roadmap

2. HealthLink_System_Context_and_Developer_Documentation.md
   → conceptual and workflow context

3. Original proposal
   → product motivation and project scope
```

If an older design document conflicts with V6, follow V6.

