# OctaneOS Workshop Beta state
Source: preserved uploaded FINAL_POLISHED, 281970 bytes, SHA256 03d3b08efc9d8166046059a45488b00e48cd079f0840174326480858aae1bba8.
Fresh baseline: 920841b6ef2fbc12aa6892d8f611fd7c0da53765. Branch build/workshop-beta. Actual release HEAD is recorded in RELEASE_CHECKPOINT.txt in the archive.
M1–M5 implemented: source recovery; authenticated API/PostgreSQL/RLS; workshop job-card UI; supported analyzer integration; reports/passport/print; guardrailed optional AI adapter.
M6 local gates: original 39 tests passed; expanded 62 tests passed; strict frontend build passed; actual Chromium end-to-end, reload, print and mobile passed. See verification/RELEASE_RESULTS.md and logs for subsequent focused test.
Changed areas: backend/app/workshop, migrations, main integration, workshop frontend/legacy split, tests, launch/deployment artifacts and documentation.
M7: local demonstration/deployment candidate package with source, built frontend, Git bundle and screenshots. No hosted pilot claimed.
Unresolved external gates: native PostgreSQL concurrency/RLS, live Supabase identities, live AI request, Docker build/startup, authorized deployment.
Next action: use supplied local launcher; for pilot, configure authorized staging resources and run the listed external verification gates before release.
