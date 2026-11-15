# HealthLink changelog

## 1.1.0

- New and existing doctors can set up their own Citizen profile from the Professional Portal using their existing account and NID. Setup is available while a professional application is under review.
- Resume active Citizen and Professional sessions from the home page. Signing out of one portal leaves the other portal's session active.
- Add password visibility controls to Citizen registration and Professional applications.
- Update `dnspython` to 2.9.2 to address CVE-2026-128089.

## 1.0.1

- Start a browser session when citizen or professional registration succeeds. Renew active sessions in the same browser profile and synchronize sign-out across tabs.
- Show pagination only when lists span multiple pages. Keep older records accessible in long histories and search results.
- Add private inboxes with unread counts for citizens, professionals, and admins. Deliver medicine and appointment reminders in-app and surface appointment, diagnostic, and professional verification updates.

## 1.0.0

- First release to carry a semantic version across the API and frontend.
- The release workflow verifies the running API version on the staged deployment and the production domain. Its summary records the version and exact Git commit.

The preceding production release is commit `d60c172`, with diagnostic lab sessions and PDF reports at database migration `0033_diagnostic_sessions`.
