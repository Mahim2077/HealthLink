# Phase 32 production closure

Phase 32 and the existing phased plan closed on 2026-11-05 after GitHub Actions promoted the verified build and the live checks passed.

| Release evidence | Result |
| --- | --- |
| Repository and branch | [Mahim2077/HealthLink main](https://github.com/Mahim2077/HealthLink/tree/main) |
| Application commit | [45dd3110d980bf674b88526a631afd44be0af4cb](https://github.com/Mahim2077/HealthLink/commit/45dd3110d980bf674b88526a631afd44be0af4cb) |
| CI/CD | [Run 41980961506](https://github.com/Mahim2077/HealthLink/actions/runs/41980961506) succeeded under Mahim2077 |
| Vercel | `mahim2077s-projects / healthlink-sd`, project `prj_kQyhfaS1tFS7NXlUMYr9C0FA8W5f` |
| Promoted deployment | `dpl_E1Ng8WwkbEtpumyJ1tkAuRPu6Vrb`, READY in production |
| Stable domain | [healthlink-sd.vercel.app](https://healthlink-sd.vercel.app/) resolves to the promoted deployment |
| Production Alembic head | `0031_ai_conversations` |
| Prior READY deployment | `dpl_3RyPMHxWh3BVG6pgsrEEfHQrUyGr`, application `6649931e29bdf19a9b085ec2b0641a79f97777b7` |

The initial release passed both quality jobs. Its Vercel build stopped before staging because the pinned builder used 3.14 as its fallback when 3.12 was absent from the runner. That overrode the 3.13 pin during conversion of `requirements.txt`. The repair provisions the builder's default 3.12 interpreter in the release job. The successful build log confirms that Vercel selected 3.13 from `backend/.python-version`. [Initial run 41979382069](https://github.com/Mahim2077/HealthLink/actions/runs/41979382069) · [Vercel Python runtime documentation](https://vercel.com/docs/functions/runtimes/python)

The successful run passed the backend and frontend quality jobs, built both Vercel services, passed all nine protected staged checks, and promoted that same deployment. The workflow and an independent probe each passed all nine stable-domain checks. The stable alias and deployed commit were confirmed through the approved Vercel connection.

| Live authenticated smoke | Sign-in | Read-only overview | Logout |
| --- | --- | --- | --- |
| Citizen | 200 | 200 | 204 |
| Doctor | 200 | 200 | 204 |
| Admin | 200 | 200 | 204 |

The authenticated checks verified role identity, the overview response contract, and test-session logout. They covered production authentication and database reads. The [closing verification report](PHASE_32_CLOSING_RELEASE_CHECK_2026_11_04.md) records local synthetic browser and clinical lifecycle evidence.
