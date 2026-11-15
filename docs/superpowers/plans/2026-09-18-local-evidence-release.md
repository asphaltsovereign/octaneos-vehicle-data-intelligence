# Sentinel Local Evidence Release Implementation Plan

**Goal:** Deliver the approved evidence-first local software release, with cloud AI deferred.

**Architecture:** Keep FastAPI, PostgreSQL/WASM, tenant checks and immutable reports. Add a compact report-index endpoint and a modular React evidence workspace; retain the existing intake and review components. No automatic seed records or external calls.

**Tech stack:** Existing React/TypeScript/Vite, FastAPI, psycopg, PGlite. No new application dependencies.

## Approved design and constraints

- Local Windows application with a SaaS-style responsive graphite/amber interface, not a hosted production service.
- Overview, vehicles/passports, evidence library, investigations/workshop queue, customer directory, data governance.
- Dashboard values derive from stored records; explicitly label loaded-record limits. Empty state provides actual next actions.
- Report chart displays saved telemetry in physical units with timestamp-based spacing, gaps for missing values and source labels. No invented health scores or sample data.
- Cloud AI is deferred. Report explanation uses deterministic local evidence only in the demonstration launcher.
- Preserve original evidence, tenant boundaries, source labels, model fallback disclosures, print workflow and migration compatibility.
- Correct uvloop's platform marker in the pinned Windows dependencies.
- Deliver a separate ZIP; never include local databases, keys, virtual environments or node_modules.

## Task 1 — Report index and local explanation

Files: backend/app/workshop/api.py, tools/run-demo.py, backend/requirements-lock.txt, backend/tests/test_evidence_workspace.py.

- [ ] Run the existing test suite and frontend build.
- [ ] Write integration tests: GET /api/reports returns own report metadata and counts, excludes raw analysis, and denies other tenants. Empty tenant returns [].
- [ ] Run tests and observe missing route failure.
- [ ] Implement a membership-checked SELECT with LEFT JOIN review notes, count findings in JSONB, exclude telemetry payload. Return up to 1000 newest items.
- [ ] Force OCTANE_AI_PROVIDER=none in the local launcher; test local explanation returns deterministic_local even with inherited cloud settings using the launcher environment helper.
- [ ] Add sys_platform marker to uvloop; evaluate the requirement marker for win32/linux.
- [ ] Run the tests to green.

## Task 2 — Evidence workspace

Files: frontend/src/Workshop.tsx, frontend/src/workspace/Workspace.tsx, frontend/src/workspace/Telemetry.tsx, frontend/src/workspace/theme.css, tools/browser-workflow.cjs.

- [ ] Extend real-browser workflow to expect overview, searchable vehicle/report lists, source filters, manual-report no-telemetry state and saved telemetry chart.
- [ ] Run against old UI and observe missing overview failure.
- [ ] Implement navigation and data fetching using the existing authenticated API; extract overview, directory, report register and governance components into Workspace.tsx.
- [ ] Add charts to report details; select a signal, preserve null gaps, label x/y axes, display exact values for selected samples.
- [ ] Apply responsive dark design tokens, compact tables, overview status pipeline, clear empty/error/loading states, and white print treatment.
- [ ] Run typecheck/build and browser workflow through create, report, review, close, reload, search, passport and invalid CSV.

## Task 3 — Release

Files: README_LOCAL_RELEASE.md, verification/LOCAL_RELEASE_RESULTS.md, START_WORKSHOP_WINDOWS.ps1.

- [ ] Run backend regression tests, frontend build and browser tests at 1440/390 pixels.
- [ ] Inspect rendered screenshots and verify print PDF generation.
- [ ] Document checks actually run; native Windows and hosted production remain unverified here.
- [ ] Commit only release code/docs/tests, archive tracked source plus prebuilt dist and verification results into a separate ZIP, test ZIP integrity and save deliverable.
