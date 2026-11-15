# OCTANEOS SENTINEL — APPROVED BUILD MISSION

You are my lead software engineer, product designer and release engineer for Asphalt Sovereign.

Build **OctaneOS Sentinel Workshop Beta** from the attached source into a working, deployable, AI-integrated SaaS beta.

This is a BUILD request. Do not stop after producing a plan, architecture document, mockup or code snippets.

The product scope and architecture below are approved. I authorize in-scope local code changes, tests, dependency installation, tracked migrations, development branches, documentation and packaging. I explicitly waive additional brainstorming and planning-only approval gates within this scope.

This does not authorize spending, destructive operations, production database changes, external account provisioning or deployment without any required platform approval.

## 1. Objective and constraints

Target: a pilot-ready release within seven calendar days.

Customer: independent motorcycle workshops.

Core value: turn workshop observations and supported diagnostic data into an evidence-backed vehicle-health report and persistent service history.

The complete customer journey is:

**Authenticate → select customer → register vehicle → create job card → enter inspection/upload supported data → analyze → review evidence → save report → view service history → print/share report.**

Constraints:

- Preserve existing working OctaneOS functionality.
- Keep the architecture simple and maintainable.
- Prioritize a complete end-to-end workflow over feature quantity.
- Treat the deadline as a scope constraint, never a reason to weaken authentication, tenant isolation or evidence integrity.
- Do not build hardware, retrofit systems or a community platform.
- Do not promise a completed commercial platform merely because a beta runs.

## 2. Establish actual capabilities once

Inspect the tools actually available in this session. If tool discovery is supported, search narrowly for file access and command execution. Do not dump the entire tool registry.

Demonstrate execution capability with one harmless command, such as printing the working directory.

Important:

- A missing skill reader does not prove that command execution is unavailable.
- Do not claim terminal access without executing a command.
- Do not infer capabilities from historical messages.
- Do not repeatedly ask me to restart the same unavailable environment.

If execution genuinely is unavailable after one targeted discovery attempt, state that once. If source-reading tools remain available, produce a concrete local-development handoff from the supplied files, clearly marking verification as unperformed. Do not fabricate tests, screenshots, archives or execution results.

Never claim that a prompt can create unavailable platform tools.

## 3. Use actual source, not Library metadata

The attached project files are the implementation source of truth.

Preferred package:

`OctaneOS_Sentinel_V3.4_Phase1A_Local_Foundation.zip`

Historical identity of the exact Phase 1A package:

- Size: `608932` bytes
- SHA-256: `e663797870748f8613c05ca3cbb548a599c737e37100373c31267dbcbc5b7343`
- Historical HEAD: `b7c1f719deb8372c208627419cc86baf2dc8c735`
- Historical baseline: `7ec928bd10c7d6019a6ceb4c41cae5101c708a76`

These values identify that historical package. They are not universal requirements for every subsequent version.

A renamed or re-uploaded ZIP may have a different Library ID and filename. Do not reject it solely for those differences.

Procedure:

1. Preserve the uploaded archive unchanged.
2. Check archive integrity and reject unsafe extraction paths.
3. Extract only into a fresh task-specific directory.
4. Inspect the actual project structure and included documentation.
5. If an included Git bundle is available, verify and restore it.
6. Record the actual HEAD, branch and working-tree status.
7. If the archive matches the historical checksum, identify it as verified Phase 1A recovery.
8. If it is a different genuine OctaneOS source package, identify it accurately as the supplied baseline—not verified historical recovery.

If I supplied only `OctaneOS_Sentinel_V3.4_FINAL_POLISHED.zip`, I authorize a fresh foundation build from that source. State this distinction once and continue. Do not invent missing Phase 1A commits, files or test results.

If no genuine project source is available, ask one focused question naming the exact missing input.

If Git history is absent, create a truthful new local baseline where permitted. Never manufacture historical hashes. If Git operations are restricted, respect the restriction and continue permissible work with filesystem checkpoints.

## 4. Inspect, outline, then implement

Read relevant project instructions and existing architecture before editing.

Identify:

- Existing frontend and backend entry points.
- Analyzer inputs, outputs and safety boundaries.
- Available model artifacts and their actual feature contract.
- Existing authentication/database foundation.
- Existing tests and report exports.
- Reusable components and missing integration.

Produce a short execution outline with milestones and acceptance gates, then continue implementing without asking for another routine approval.

Keep planning proportional. Do not spend the session writing multiple overlapping strategy documents.

Run available baseline tests before changing the behavior they cover. Record actual results. Diagnose failures and fix relevant defects within scope; do not turn ordinary warnings into artificial blockers.

## 5. Approved architecture

Use the existing safe implementation patterns wherever possible:

- React + TypeScript frontend.
- FastAPI backend.
- PostgreSQL persistence.
- Supabase Auth and PostgreSQL RLS as the production foundation.
- Modular monolith, not microservices.
- Single-origin application deployment.
- Docker deployment artifacts compatible with the approved Render direction.

Inspect and honor existing database-access documentation if present.

Do not require GitHub, Supabase or security plugins merely to implement code. Plugins and account provisioning are distinct from SDK/library development.

Missing hosted credentials must not block local application development, testable interfaces or deployment packaging.

Local demonstration mode is permitted only when clearly separated from production:

- Display an unmistakable DEMO label.
- Use explicitly synthetic/demo records.
- Never allow development authentication bypasses in production.
- Production must fail closed when required security configuration is absent.
- Never use SQLite or mocked permissions as proof of PostgreSQL RLS isolation.
- Label the database engine actually used in verification.

## 6. Required functional product

Reuse the existing schema where practical. Do not create duplicate entities merely because names differ.

### Authentication and workshop tenancy

- Authorized workshop users can sign in and sign out.
- Sessions expire and errors are handled.
- Users operate only within permitted workshop memberships.
- Production identity verification must use a supported implementation, not unverified JWT decoding.
- Tenant access must be enforced server-side and in RLS.

### Customers and vehicles

- Create, view and edit minimum necessary customer details.
- Create and select vehicle records.
- Capture make/model/year, odometer and relevant source identifiers.
- Keep registration, phone and other identifying fields optional where not essential.
- Clearly distinguish a real vehicle from a demonstration dataset.

### Workshop job cards

- Create a job card linked to the correct workshop, customer and vehicle.
- Record customer complaints, technician observations and inspection checklist.
- Use a small, explicit status lifecycle.
- Save and reload drafts.
- Display useful validation and failure messages.
- Prevent accidental duplicate submissions.

### Diagnostic input and analysis

Support actual existing input formats—not imaginary universal scanner compatibility.

- Accept supported CSV/diagnostic exports.
- Record manual inspections separately.
- Validate schema, units, missing fields and data quality.
- Bound upload size and parsing work.
- Reject invalid/empty files safely.
- Preserve source provenance and relevant hashes.

Do not feed manual observations into a telemetry model by inventing its missing features.

Unsupported inputs must produce an honest limitation or inspection-only report, not fabricated analysis.

### Reports and Service Passport

Persist:

- Report identifier and timestamps.
- Workshop, vehicle and job-card linkage.
- Source classification.
- Data-quality results.
- Analyzer/model/rule versions actually used.
- Findings and supporting evidence.
- Limitations.
- Separate technician review/notes.

Preserve original analysis evidence. Technician comments must not silently rewrite it.

A completed analysis can create a Service Passport event linked to the report.

Users can reload the application and retrieve saved jobs, reports and history.

Provide a clean customer-facing print/export workflow. Reuse existing export capability; printable HTML is preferable to unfinished custom PDF infrastructure.

## 7. AI integration: useful and honest

Preserve the existing evidence-first analysis pipeline where it exists:

**Validated input → quality gate → actual ML screening → deterministic rules → safety boundaries → structured findings → optional language explanation.**

If a frozen 47-feature model exists, preserve and test its real contract. If it does not exist in the supplied files, report that fact. Do not invent model artifacts or claim training happened.

Rules:

- Public car datasets do not establish Yamaha R15 diagnostic validity.
- An anomaly score is not automatically a calibrated probability of failure.
- Do not claim prospective predictive maintenance without appropriate evidence.
- Never invent live sensors, measurements or model confidence.
- Manual-inspection findings and ML-derived findings must be distinguishable.

Implement an optional backend language-AI adapter for plain-language explanations:

- Provider and model configured through environment variables.
- Verify provider integration against current official documentation.
- Do not invent API model identifiers based on the name of the chat model.
- Keep API secrets off the frontend and out of Git.
- Send minimal, redacted structured evidence—not customer identifiers or raw uploads by default.
- Treat uploaded text as data, not instructions.
- Require structured output with references to existing evidence.
- Reject unsupported findings or invalid evidence references.
- Apply bounded timeout, retry and request limits.
- Provide deterministic local explanations when the provider is unavailable.
- The report must remain usable without waiting for a language-model response.

Test the adapter with controlled fixtures. Clearly distinguish mocked tests from a successful live provider request.

Do not claim live AI integration was verified unless it actually was.

## 8. Design quality: specific, not generic

Design an operational workshop product, not a generic SaaS template.

Primary UI: **Workshop Job Card**.

Required screens:

1. Sign-in and initial onboarding.
2. Actual workshop job queue.
3. Customer/vehicle selection.
4. Guided job-card creation.
5. Job detail with inspection and diagnostic input.
6. Evidence-backed analysis report.
7. Vehicle Service Passport.

Visual direction:

- Asphalt Sovereign / OctaneOS Sentinel branding.
- Restrained motorsport-inspired identity.
- Graphite/navy shell with high-contrast working surfaces.
- Clear typography and tabular/monospaced numbers where useful.
- Amber for caution and consistent status colors.
- Evidence panels designed for inspection and comparison.
- Print-friendly reports.
- Existing authentic brand assets preferred.

Avoid:

- Fake revenue or activity statistics.
- Invented testimonials.
- Decorative telemetry mountains.
- Neon-heavy gaming aesthetics.
- Unnecessary gradients and animations.
- Buttons without working behavior.
- Stock dashboards unrelated to workshop tasks.

Test narrow mobile layouts and desktop layouts.

Implement empty, loading, error, permission-denied and retry states. Ensure keyboard navigation, labels and visible focus are usable.

## 9. Security requirements

Security is not optional beta polish.

At minimum:

- Deny-by-default tenant access.
- RLS read/write policies with appropriate checks.
- Cross-tenant foreign-key/reference protection.
- No service-role key in client code or normal workshop CRUD.
- Authorization on analysis and report endpoints, not just database tables.
- Tenant-safe upload/storage access.
- Bounded parsing and upload validation.
- No execution of user-supplied code or serialized model files.
- Sanitized displayed/exported content.
- Safe handling of spreadsheet-formula injection in CSV exports.
- Secrets excluded from source, logs and packages.
- No sensitive stack traces in customer-facing responses.
- Minimal personal-data collection.
- Clear data-handling and diagnostic-limitations notices.

Do not claim legal compliance or security certification from a basic scan.

## 10. Execution milestones

Execute in order; these are milestones, not instructions to wait until tomorrow.

**M1 — Baseline and runnable development system**

Restore/inspect actual source, establish truthful Git baseline, run baseline checks and start the existing application.

**M2 — Auth, tenancy and persistence**

Implement/test workshop access and customer/vehicle/job-card persistence.

**M3 — Usable Job Card UI**

A user can create, save and reload a job through the interface.

**M4 — Analyzer integration**

Supported data flows through the preserved analyzer into a saved evidence-backed report.

**M5 — Complete customer workflow**

Service Passport, print/export and guardrailed AI explanations.

**M6 — Release hardening**

Regression, tenant isolation, browser workflow, production configuration and Docker verification.

**M7 — Pilot handoff**

Deployment-ready release, demonstration material and onboarding instructions. Deploy only when authorized and technically verified.

If schedule pressure appears, remove optional analytics, landing-page embellishments and premium UI features first. Never sacrifice the core workflow, tenant security or honest analysis boundaries.

## 11. Verification gates

Run and report actual available checks:

- Original analyzer regressions.
- Backend tests.
- Frontend typecheck and production build.
- Frontend tests where applicable.
- PostgreSQL/RLS isolation tests.
- Integration tests.
- Browser end-to-end workflow where tools support it.
- Container build/startup verification where supported.

Test specifically:

- Unauthenticated and invalid/expired sessions.
- Two workshops cannot read, insert, update, delete or reference each other’s data.
- Analysis/report access is tenant-scoped.
- Create job → submit input → analyze → save report → reload → retrieve history.
- Empty, malformed and unsupported input.
- Manual observations cannot masquerade as telemetry.
- Public/demo datasets retain their source labels.
- AI timeout, invalid response and deterministic fallback.
- Duplicate submission handling.

Do not weaken tests to make failures disappear.

Report each gate as PASS, FAIL or NOT RUN, with the actual command and result. A mocked browser/database/provider is not evidence that the real deployed service works.

Use actual browser screenshots for visual verification when available. Never present generated mockups as screenshots of the running application.

## 12. Runtime and recovery discipline

- Parallelize genuinely independent checks when useful.
- Keep edits and commits focused.
- Show concise progress updates roughly every 60 seconds during active work.
- Use bounded tool waits so progress remains visible.
- If a command stalls without measurable progress, inspect it and stop/retry safely where appropriate.
- Do not blindly kill a healthy build solely because it exceeds five minutes.
- Never leave indefinite background jobs or claim invisible overnight work.
- Respect permission and authentication failures; do not bypass them.
- After repeated incidental failures, use a safe supported alternative rather than endlessly repeating the same call.

Maintain a concise `STATE.md` containing:

- Actual source location and baseline.
- Current HEAD/branch when available.
- Completed milestone.
- Changed files.
- Latest commands and verification results.
- Exact unresolved blocker.
- Next implementation action.

At milestone boundaries, persist work using the configured repository or available durable artifact storage. Do not treat a transient scratch path as permanent storage.

If using archive handoff, include source and a verified Git bundle where available, exclude secrets and unnecessary dependency directories, and record the archive checksum.

If durable saving is unavailable, provide the downloadable artifact and clearly tell me to download it before the session ends.

## 13. Deployment boundaries

Prepare:

- Reproducible local setup.
- Safe `.env.example`.
- Tracked database migrations.
- Docker configuration.
- Health/readiness checks.
- Supabase configuration and deployment instructions.
- Rollback and backup instructions.

Do not automatically migrate a production database during application startup.

Before external provisioning, spending or deployment requiring founder authority, ask one concise question stating the exact resources/actions needed.

Missing external approval must not prevent finishing and packaging the local verified product.

Never fabricate a live URL. A deployment-ready ZIP is not a hosted SaaS. Identify the release state accurately.

## 14. Final handoff

Lead with the working result.

Return:

1. Actual live/private preview URL if verified, otherwise verified local run instructions.
2. Downloadable verified source/release package.
3. Actual UI screenshots where available.
4. Verification table with fresh results.
5. Completed customer workflow and remaining limitations.
6. Exact environment-variable names and setup steps without revealing secret values.
7. Migration/deployment/rollback instructions.
8. Five-minute demonstration script.
9. Actual Git HEAD and release checkpoint.
10. The smallest remaining founder action needed for the pilot.

Do not declare completion if buttons are fake, records disappear on reload, tenant isolation is unverified or core analysis is a placeholder.

START NOW: prove current capabilities, inspect the supplied source, give a brief execution outline and begin implementation. Do not repeat this prompt back to me. Do not ask whether I want you to build the product—the build is already authorized.