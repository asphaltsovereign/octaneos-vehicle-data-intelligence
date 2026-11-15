# Sentinel Local 0.2 — Release checks

Environment: Linux, Python 3.12.14, Node.js 24.19.0, Chromium 153, PGlite/WASM PostgreSQL.

- Baseline: 62 backend tests passed before changes.
- Added integration tests: report register membership scope, compact serialization, counts and saved-review presence passed (2 tests).
- Final backend regression suite: 64 tests passed, 1 existing deprecation warning.
- Chart tests: elapsed-time positioning, missing-value discontinuities, entirely missing/constant signals and small-range axis precision passed (4 tests).
- uvloop platform marker evaluated successfully: excluded on win32, included on Linux.
- Frontend TypeScript check and optimized Vite build passed.
- Chromium end-to-end test passed at 1440×1000 and 390×844: demo entry, empty overview, customer/vehicle creation, job intake, manual inspection, saved report, notes, local explanation, PDF printing, review/close, reload, passport reopening, report search/source filters, invalid CSV rejection, synthetic CSV screening, chart signal selection and sample slider, correct report counts, vehicle search and governance page.
- Browser recorded zero uncaught page errors and no horizontal overflow on the tested mobile report page.
- Screenshots and a synthetic sample PDF are included in this directory. Screenshots use deliberately created test data; application workspace starts empty.

Limitations: tests ran in Linux. Native Windows launcher execution, hosted authentication, native PostgreSQL concurrency, real SAN-V1 acquisition, cloud AI, Docker deployment and real workshop validation were not performed. No frozen trained artifact is bundled. Local runtime always disables cloud AI and uses the existing deterministic explanation.

The existing Starlette/AnyIO deprecation warning does not fail the backend tests. npm reports an environment-level http-proxy configuration warning; typecheck and build complete successfully.
