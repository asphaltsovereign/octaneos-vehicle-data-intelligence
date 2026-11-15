# Workshop Beta implementation plan
Spec: docs/BUILD_MISSION.md. Approved scope; execute without planning approval.
Baseline: 920841b6ef2fbc12aa6892d8f611fd7c0da53765, supplied FINAL_POLISHED; no frozen model binary.

1. Preserve baseline and run original pytest + frontend build.
2. Add backend/app/workshop/{auth,db,schemas,api,evidence}.py and migrations/001_workshop.sql. Test real PostgreSQL RLS, denied references and persisted workflow before implementing endpoints. Dedicated restricted DB role; verified Supabase user; explicit development demo only.
3. Add frontend/src/Workshop.tsx and workshop.css, preserve original main as Legacy.tsx. Consume API_CONTRACT.md. Test real browser journey, persistence and mobile layout.
4. Add bounded evidence-only OpenRouter adapter and tests. Language model selects approved evidence explanations; cannot introduce new claims. No frozen-model claim without artifact.
5. Regression, production fail-closed tests, browser run, migration checks, source bundle, instructions and screenshots. Container gate only when Docker available.

Acceptance: create customer/vehicle/job, save inspection, analyze supported upload or inspection, reload saved immutable report/passport, print. Two tenants isolated in API and PostgreSQL. No external deployment without founder approval.
Ruling: use PGlite PostgreSQL/WASM for local runtime because native installation was denied; do not present it as hosted Supabase or native PostgreSQL validation.
