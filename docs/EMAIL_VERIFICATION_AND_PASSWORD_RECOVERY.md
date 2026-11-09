# Email verification and password recovery

New Citizen and Professional registrations require proof of email ownership when `AUTH_EMAIL_OTP_ENABLED` is enabled. Professional applications still require the existing administrative review. Existing users can verify their recovery email in **Settings → Security**. An administrator changing a citizen's email clears the previous verification.

Citizen and Admin password recovery uses the account email. Professional recovery uses National ID and role. Reset requests return a neutral response, and a completed reset revokes the account's existing sessions. The backend stores keyed digests for email codes and reset tokens. Codes expire after ten minutes, are limited to five verification attempts, and have a one-minute resend cooldown. Persistent limits also apply to requests and deliveries.

The release includes clearer duplicate-registration messages, password validation in the registration forms, and an audited profile editor in Admin Citizen Identity Support.

## Configuration and rollout

Apply Alembic revision `0032_auth_email_codes` before starting the new backend. The migration adds verification metadata, challenges, and rate limits. Existing accounts keep access and can enroll a recovery email when ready.

Set the following backend variables in the Vercel project's **Production** environment. Store the SMTP key and a fresh OTP signing secret as private **Secret** variables. Use a production SMTP credential and verified Brevo sender. Keep local values in the ignored `backend/.env` file.

| Variable | Production setting |
| --- | --- |
| `AUTH_EMAIL_OTP_ENABLED` | `true` to enable verification and recovery |
| `AUTH_EMAIL_OTP_SECRET` | A separate random secret of at least 32 bytes |
| `AUTH_SMTP_KEY` | Brevo SMTP key |
| `AUTH_SMTP_USERNAME` | Brevo SMTP login |
| `AUTH_SMTP_FROM_EMAIL` | Verified sender email address |
| `AUTH_SMTP_HOST` | Defaults to `smtp-relay.brevo.com` |
| `AUTH_SMTP_PORT` | Defaults to `587` with STARTTLS. Port `465` uses implicit TLS. |

The release pipeline applies the migration, builds both services, stages the production deployment without assigning the live domain, and checks public and protected routes. Confirm signup and password reset email delivery from the staged deployment with an inbox controlled by the project owner before promoting it. A reset API response alone does not confirm email delivery.

For an operational rollback, use the previous production deployment or disable `AUTH_EMAIL_OTP_ENABLED` and redeploy. Leave the additive migration in place so the newer backend can start when service resumes.

## Local verification

The local preview completed Citizen email verification and account creation using Brevo. The production frontend build, 353 frontend tests, targeted OTP tests on SQLite and PostgreSQL, dependency audits, and exact Python lock reproduction passed. The migration applied cleanly from `0031_ai_conversations` with no metadata drift. Hosted email delivery remains a release check.
