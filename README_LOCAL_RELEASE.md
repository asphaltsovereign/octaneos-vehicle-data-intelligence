> Recovered archive instructions. A fresh Git clone must install and build the frontend first; use the current root README for the complete setup.

# OctaneOS Sentinel Local 0.2

Working evidence-first local application by Asphalt Sovereign. The interface is designed as a SaaS workspace; this ZIP is NOT a hosted production SaaS service. Cloud AI is intentionally deferred. Use synthetic/test records only.

## Start on your Windows laptop

1. Stop the old application with Ctrl+C in its PowerShell window.
2. Extract this ZIP to a NEW folder. Keep the previous folder as a backup.
3. Open `octaneos-sentinel-v3` and double-click `START_SENTINEL_WINDOWS.cmd`.
4. If you prefer PowerShell, open it in this folder and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\START_WORKSHOP_WINDOWS.ps1
```

5. Wait for `Application startup complete`, then open http://127.0.0.1:8000.
6. Select **Enter demonstration workshop**. No email, password or AI key is required.
7. Name the workspace. Keep the terminal open while using Sentinel; Ctrl+C stops it.

Prerequisites: Python 3.12 (with the `py` launcher) and Node.js 22 or newer. The first start needs internet to install dependencies. The compiled frontend is included; no separate frontend terminal is needed. The uvloop Windows installation problem is fixed with a platform marker in the dependency lock. Native Windows execution of this release has not been tested in the Linux build environment.

If port 8000 or 55432 is in use, close the old Sentinel instance before restarting. Do not terminate unrelated programs. If the browser shows the previous interface, press Ctrl+F5.

## First complete workflow

1. **Customers & bikes:** add a fictional customer, then add a motorcycle. All vehicles in the local demo are labelled demonstration records.
2. **Job queue → New job card:** choose that customer and motorcycle, record a complaint.
3. Record observations, then mark inspection items Pass / Needs attention / Not checked.
4. Select **Create inspection report** for a manual report. Manual inspection does not run the telemetry model.
5. Alternatively, choose `samples/normal.csv` or `samples/voltage_degradation.csv` from this extracted folder. Select **Synthetic**, then **Validate & analyze**. These files are demonstrations, not measurements from a real R15.
6. Inspect the saved telemetry chart; choose speed/RPM/battery/load/anomaly score and move the sample slider. Unmeasured signals remain missing.
7. Save technician notes; **Explain findings** provides a deterministic local explanation, not cloud AI.
8. **Mark reviewed**, then **Close job**. Use **Print / save PDF** to export the report through your browser.
9. Search the **Evidence library**, or open **Vehicles & passports → Open passport** to revisit the report.

Overview metrics come from saved records. An empty workspace intentionally starts at zero. Registers load the latest 1,000 records each; displayed counts are loaded-record counts, not unlimited historical totals. Reports are not automatically seeded.

## Existing records from the previous ZIP

No schema change is required for this release. The data lives in `tools/.local-postgres` inside the project folder (File Explorer may require hidden items enabled).

To carry over demo records, stop BOTH versions first. Make a backup copy of the old project's entire `tools/.local-postgres` folder. Before starting the new copy for the first time, copy that folder into the new project's `tools` directory. Do not merge two existing database folders or copy while either application is running. Keep the old folder untouched until you have opened and checked the records in the new version.

Browser sessions expire on server restart. Enter the demonstration workshop again to access saved records. A ZIP download does not contain your laptop's database or credentials.

## What is included

- Evidence overview with stored-record counts and investigation pipeline.
- Searchable vehicle/passport register and source-filtered evidence library.
- Customer and motorcycle creation/editing, guided job intake, status filtering.
- Manual inspection and supported CSV analysis with persisted reports.
- Timestamp-based telemetry charts, sample inspection and missing-signal handling.
- Technician review notes, local explanations, review/close lifecycle and print output.
- Data-governance page explaining provenance, model runtime and limitations.
- Mobile layout with navigation drawer and bottom navigation.

## Boundaries

- Not public-hosted; do not expose the local demo server to the internet.
- Not a validated motorcycle diagnosis, predictive-maintenance or ethanol-compatibility product.
- No frozen trained artifact was supplied. Telemetry reports disclose the actual session-fitted fallback runtime; manual reports disclose that no telemetry model ran.
- Raw CSV files are not retained. Saved reports contain derived evidence, chart preview points and provenance/hash metadata.
- Cloud AI, live SAN-V1 streaming, billing, inventory, multi-branch operations and subscription management are not part of this release.
- Hosting, production identity, native PostgreSQL concurrency, backup/restore drills and real workshop validation remain future verification gates.

## Developer checks

```bash
npm --prefix frontend ci
npm --prefix frontend run build
node --test tools/chart-math.test.mjs
.venv/bin/python tools/verify-local.py
```

The chart unit-test command uses Node.js 24's TypeScript stripping; application operation still supports Node.js 22+. Backend verification uses a disposable local PGlite database. The browser test uses `tools/browser-workflow.cjs` with Playwright and Chromium, not production credentials. See `verification/LOCAL_RELEASE_RESULTS.md` for the actual tested environment and limitations.
