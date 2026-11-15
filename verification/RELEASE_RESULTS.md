# Release verification — Workshop Beta 0.1

Supplied baseline: FINAL_POLISHED ZIP, 281970 bytes, SHA-256 `03d3b08efc9d8166046059a45488b00e48cd079f0840174326480858aae1bba8`. ZIP CRC and extraction-path checks PASS. Fresh Git baseline `920841b6ef2fbc12aa6892d8f611fd7c0da53765`; not historical Phase 1A recovery.

| Gate | Result | Actual command/evidence |
|---|---|---|
| Original backend baseline | PASS | `cd backend && ../.venv/bin/python -m pytest -q` before changes: 39 passed |
| Backend regressions + workshop/security | PASS | `.venv/bin/python tools/verify-local.py`: 62 passed, one dependency deprecation warning; `tests.log` |
| Workshop/RLS/evidence tests | PASS | `.venv/bin/python tools/verify-local.py tests/test_workshop.py tests/test_workshop_security.py`; `workshop-final.log` 22 passed; includes successful synthetic CSV persistence |
| Frontend typecheck and build | PASS | `npm --prefix frontend run build`; `frontend-build.log` |
| Browser workflow, persistence, print | PASS | `CHROMIUM_PATH=... .venv/bin/python tools/verify-local.py --browser`; actual Chromium workflow; `browser-result.json` |
| Mobile horizontal overflow | PASS | Browser viewport 390×844; no horizontal overflow |
| PostgreSQL RLS | PASS in PGlite/WASM | Real SQL policies/constraints executed through psycopg; two fixture identities, denied cross-tenant select/insert/update/delete/references, immutable evidence |
| Native PostgreSQL concurrency / hosted Supabase RLS | NOT RUN | Native PostgreSQL installation unavailable; do not substitute PGlite evidence |
| Supabase live sign-in/expiry | NOT RUN | Hosted credentials unavailable. Production config/legacy-route denial tested |
| Live OpenRouter request | NOT RUN | No key/model configured; adapter success, invalid references/claims and timeout tested with controlled HTTP fixtures |
| Docker build/startup | NOT RUN | Docker unavailable; reviewed artifacts supplied |
| Windows launcher | NOT RUN on Windows | Linux implementation/testing environment; manual setup also documented |
| External deployment | NOT RUN | Not authorized/provisioned; no live URL claimed |

The browser journey created a synthetic customer, vehicle and job; saved inspection; generated report; saved notes; requested local explanation; printed; reviewed and closed the job; reloaded and retrieved it; opened the passport/report; checked mobile; signed out. Screenshots are real captures. `sample-report.pdf` is a real browser-generated print export.

The original laboratory presentation tests were updated only to read `Legacy.tsx`, the moved original UI; assertions were preserved. Regression tests run with explicit development demo mode because production now disables unauthenticated lab endpoints.

Local limitations: list endpoints cap at 1,000 records without pagination; membership invitation is administrative; one app process only for in-memory rate limits/revocation; no public report-share URL; no frozen model packaged. Do not use demo mode for customer information. Real pilot readiness remains conditional on native/hosted/container gates.
