> Recovered archive instructions. A fresh Git clone must install and build the frontend first; use the current root README for the complete setup.

# OctaneOS Sentinel Workshop Beta

This release adds a working workshop flow to the supplied FINAL_POLISHED analyzer: customer → motorcycle → job → inspection/CSV → saved evidence report → technician review → Service Passport → print/save PDF.

**Release state: local beta and deployment candidate, not a hosted pilot.** Production Supabase sign-in, native PostgreSQL concurrency/RLS and Docker startup must be verified in the target environment before accepting real customer data. The local demo uses PostgreSQL compiled to WebAssembly (PGlite), not SQLite. No frozen trained model binary was present in the supplied ZIP; telemetry uses the preserved session-fitted screening fallback. It is not a calibrated failure predictor or validated Yamaha R15 diagnosis.

## Run on Windows

Install Python 3.12 and Node.js 22 or later. Extract this ZIP. Open PowerShell in its `octaneos-sentinel-v3` folder and run:

```powershell
.\START_WORKSHOP_WINDOWS.ps1
```

If PowerShell does not permit scripts, run the commands below manually. No hosted account or AI key is needed for demonstration.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-lock.txt
npm --prefix tools ci --omit=dev
.\.venv\Scripts\python.exe tools\run-demo.py
```

Open **http://127.0.0.1:8000**, choose **Enter demonstration workshop**, and name the workspace. Enter synthetic records only. No demo password exists. Records persist under `tools/.local-postgres`; sessions expire after eight hours or on server restart. Sign in again to recover records. Ctrl+C stops the application and local database. The launcher listens only on localhost. The Windows launcher is supplied but was not executed on Windows in this Linux session.

## Linux/macOS

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements-lock.txt
npm --prefix tools ci --omit=dev
.venv/bin/python tools/run-demo.py
```

The archive includes a built frontend. To rebuild: `npm --prefix frontend ci` then `npm --prefix frontend run build`.

## Supported data and evidence

- Manual inspection: brakes, tyres, lights, leaks, battery; observations and complaint are saved separately. No manual entry is fed to the telemetry model.
- Telemetry: one VED vehicle/trip CSV or SAN-V1 `schema_version=1.0`. Limits: 2 MiB, 20,000 samples, 64 columns, at least 12 rows, strict increasing timestamps. SAN requires finite usable speed and battery data plus strictly increasing integer sample sequence. Expected physical units follow the original headers, not arbitrary scanner exports.
- VED headers/aliases are in `backend/app/services/ingestion.py`; supplied `samples/normal.csv` and `samples/voltage_degradation.csv` are **synthetic VED-shaped demonstrations**, not real R15 data. Choose Synthetic and a demonstration vehicle.
- Real SAN uploads require a real vehicle and matching registered Telemetry vehicle ID. This association verifies supplied identifiers, not sensor authenticity.
- Reports and passport events cannot be rewritten/deleted by the normal application role. Technician notes live separately. Original inspection and vehicle identity snapshots are retained.
- Print/save PDF is the sharing workflow. There is no public report link, raw-upload storage or CSV export in the workshop beta.

## Production setup and deployment

See `docs/DEPLOYMENT_WORKSHOP.md`. Use the exact variables in `backend/.env.example`. No credentials are embedded in the frontend. The frontend and API share one origin. Supabase handles production identities; the backend verifies each bearer token with Supabase's authenticated user endpoint and queries PostgreSQL under a restricted role and transaction-local user identity. Every workshop request also verifies membership.

## Optional AI

`OCTANE_AI_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, and `OCTANE_AI_MODEL` enable the optional backend adapter. Choose an existing model/endpoint with structured-output support; no model identifier is guessed. The provider can select/order existing evidence explanations only. Server validation rejects unknown references, added claims, duplicates and malformed responses. Raw files, customer data and technician free text are excluded. One request, an eight-second timeout, no automatic retry, six requests/minute/user per process. Reports save before this optional call; deterministic explanations always remain available. Live cloud integration has not been verified without credentials.

## Verification

`verification/RELEASE_RESULTS.md` records actual gates and limitations. Reproduce local tests with `.venv/bin/python tools/verify-local.py`. This creates a disposable PGlite instance, applies migrations explicitly, and runs pytest. The original laboratory UI remains available only in explicit demo mode at `/?lab=1`.

Before a real pilot: run the same isolation suite against disposable native PostgreSQL, verify two real Supabase users, verify container startup and backups, then obtain deployment authorization. Do not expose the demo runtime publicly.
