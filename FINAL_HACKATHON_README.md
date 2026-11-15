# OctaneOS Sentinel V3.4 — Final Hackathon Polish

This revision is a presentation-focused repair of the working V3.4 stack. It keeps the FastAPI analysis pipeline and React/Vite architecture intact while correcting the demo-facing issues found during the final local review.

## What changed

- Replaced the single triangular synthetic speed ramp with a deterministic multi-phase urban-style drive cycle containing acceleration, cruise, deceleration, and repeated operating phases.
- Replaced the combined normalized “mountain” chart with four synchronized engineering lanes in physical units: RPM (rev/min), speed (km/h), engine load (%), and anomaly score (0–1).
- Added a clearly marked controlled-fault-injection band and separate detected-anomaly overlays.
- Reduced the Command Center to four primary metrics and removed the confusing zero-window card from fallback mode.
- Made runtime wording truthful: the UI says **checksummed frozen runtime** only when the frozen artifact is actually available; otherwise it says **labelled local fallback**.
- Added an explicit **SYNTHETIC DEMO TELEMETRY** badge so demo data cannot be mistaken for measured motorcycle telemetry.
- Changed investigation trace wording from “Frozen Ensemble” to runtime-aware “Model Screening.”

## Fastest Windows run

From the project root:

```powershell
.\START_OCTANEOS_WINDOWS.bat
```

Then open:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/health
```

If port 8000 is already occupied, stop the old OctaneOS terminal with `Ctrl+C` before launching again.

## Frozen model truth boundary

The uploaded V3.4 submission package does not contain the actual `sentinel_baseline.joblib` frozen artifact. The application therefore labels the current runtime as a local fallback unless that validated artifact is restored to:

```text
backend/artifacts/sentinel_submission_frozen/
```

Do not present fallback execution as frozen-model execution. The UI is deliberately designed to make this distinction visible.

## Render deployment

The root `Dockerfile` and `render.yaml` remain the deployment path. Render builds the React frontend, installs the FastAPI backend, and serves both from one web service. No separate frontend deployment is required.
