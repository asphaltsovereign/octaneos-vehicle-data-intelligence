> Historical README; relative links adjusted for this copy's location. Current scope is in the repository root README.

# Sentinel Local 0.2

Start with [README_LOCAL_RELEASE.md](../../README_LOCAL_RELEASE.md) for the current evidence workspace, Windows launcher, data-transfer instructions and verification boundaries. Cloud AI is deferred. The documentation below describes the prior workshop beta and original analyzer.

## Workshop Beta update

Start with [README_WORKSHOP.md](../../README_WORKSHOP.md) for this release. The following original hackathon documentation is retained as historical source context; its submission status and model claims are not current release verification.

# OctaneOS Sentinel V3

Hackathon branch of Asphalt Sovereign's OctaneOS telemetry platform.

**Submission target:** Innovation Hacks Global AI Hackathon 2026
**Final project deadline:** 10 Sep 2026, 11:23 PM IST
**Release:** V3.4 hackathon final

For paste-ready submission copy, the deadline audit, Terminal 2 findings, and the final
checklist, start with [`SUBMISSION_MASTER.md`](../../SUBMISSION_MASTER.md). The timed recording
flow is in [`docs/DEMO_SCRIPT.md`](../DEMO_SCRIPT.md).

## Mission
Turn validated telemetry ingestion into an explainable, evidence-first AI investigation workflow:

`CSV -> quality gate -> feature engineering -> Isolation Forest -> automotive rules -> evidence verification -> risk/confidence -> report`

## Current V3 seed status
- FastAPI backend
- VED-style CSV ingestion + validation
- SAN-V1 contract detection
- Windowed feature extraction
- Isolation Forest anomaly detection
- Deterministic automotive rule engine
- Evidence/contradiction investigation layer
- Unsupported-claim safety guard
- Fault injection lab endpoints
- React/Vite demo dashboard
- Automated backend tests
- V2.1 preserved under `legacy/`

## Honest scope
This hackathon branch demonstrates telemetry anomaly screening and evidence-backed investigation. It does **not** claim validated Yamaha R15 V2 fault diagnosis, ECU/DTC access, injector/ignition diagnosis, AFR/ethanol validation, or certified predictive maintenance.

## Run backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Run frontend
```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

## Fastest Windows demo path

1. Confirm the frozen model files are present under
   `backend/artifacts/sentinel_submission_frozen/`.
2. Run `VERIFY_SUBMISSION_WINDOWS.ps1` in PowerShell.
3. Double-click `START_OCTANEOS_WINDOWS.bat`.
4. Open `http://127.0.0.1:8000`.

The one-command launcher builds the frontend and serves it from FastAPI. Use the separate
Vite development server only while editing the interface.

## Backend tests
```bash
cd backend
pytest -q
```

## Hackathon demo path
1. Load the built-in normal session.
2. Run AI Investigation.
3. Inject a fault scenario.
4. Re-run the exact same analysis pipeline.
5. Compare anomaly count, risk score, evidence, contradictions and safety boundary.

## Deployment
- Frontend: Vercel
- Backend: Render/Railway/Fly.io compatible FastAPI service
- Set `VITE_API_BASE` to the deployed backend URL.

## AI provider configuration

Sentinel keeps anomaly detection and engineering rules local. The optional language-model layer receives only a compact evidence object, never the raw telemetry CSV.

Copy `backend/.env.example` to `backend/.env` and set `OPENROUTER_API_KEY`. Default routing:

- `openai/gpt-5.6-luna` — low-cost routine explanation.
- `anthropic/claude-sonnet-5` — optional Deep Investigation / engineering review.

If no API key exists or the provider fails, `/explain` falls back to a deterministic evidence summary. Core telemetry analysis therefore remains operational without a cloud LLM.

For the recorded demo, use **Instant Local**. Cloud responses can be shown separately
only after `/ai/status` reports a configured provider and a test request succeeds.

## Frozen artifact integrity

Sentinel computes the SHA-256 declared by `model_manifest.json` before joblib
deserialization. A missing, unreadable, or modified artifact never loads silently; the UI
shows a labelled fallback. The submission candidate expected by Terminal 2 is version
`sentinel-powertrain-baseline-0.5` with SHA-256
`3ee122b87fa5cadfaaa8bd5d5aff44734cddc96cc81cf32e396b6c1e5f692542`.

## Container deployment

The root `Dockerfile` builds the React frontend and serves it with the FastAPI backend as
one service. `render.yaml` is included for a Docker-based Render deployment. Configure
`OPENROUTER_API_KEY` only in the deployment secret store; never commit `backend/.env`.

## Architecture Lock — 08 Sep 2026

Sentinel V3 is frozen around an evidence-first automotive intelligence pipeline:

1. telemetry ingestion and source provenance
2. signal quality / readiness gate
3. engineering feature extraction
4. ensemble anomaly detection: Isolation Forest + PCA reconstruction + Robust-Z + EWMA + CUSUM
5. deterministic automotive rules
6. hypothesis generation with supporting and contradicting evidence
7. bounded safety-agent claim blocking
8. optional LLM explanation over structured evidence only
9. synthetic fault-injection validation harness
10. advanced telemetry / anomaly visualization layer

The ML model detects behavioural deviation; it does not claim failed components by itself. Public/synthetic data is software-validation evidence, not Yamaha R15 V2 health evidence.


## Sentinel baseline training (Sep 8 locked path)

The production anomaly path must use a frozen baseline model rather than fitting on the same session being scored. See `docs/ML_TRAINING_VALIDATION.md` and `docs/DATASET_STRATEGY.md`.

Windows PowerShell quick path from `backend/`:

```powershell
.\scripts\download_ved.ps1
# Extract the downloaded .7z with 7-Zip into data\raw_ved
python scripts/prepare_ved.py --input-dir data/raw_ved --output-dir data/prepared_ved --max-trips 80
python scripts/train_ved.py --prepared-dir data/prepared_ved --output-dir artifacts/sentinel_baseline
python scripts/validate_ved.py --prepared-dir data/prepared_ved --model-dir artifacts/sentinel_baseline
python -m pytest -q
```

Do not claim VED training as Yamaha R15 V2 validation. It is a public passenger-car telemetry baseline used to validate the Sentinel ML methodology until SAN-V1/TV-001 longitudinal data exists.

## Frozen model runtime
The production `/analyze` and `/demo` paths now prefer the frozen trained model configured by `OCTANE_MODEL_DIR` (default `backend/artifacts/sentinel_submission_frozen`). `/model/info` exposes the exact model version, SHA-256, capability boundary and validation summary. If the frozen model is absent, the API marks the result as a legacy fallback instead of silently claiming trained-model inference.
