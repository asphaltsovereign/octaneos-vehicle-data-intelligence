from __future__ import annotations

from datetime import datetime, timezone
from contextlib import asynccontextmanager
from .workshop.db import check_config, demo_mode, connection
import json
import math
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .services.ai_explainer import explain_analysis, provider_status
from .services.demo import demo_frame
from .services.ingestion import ingest_csv_bytes
from .services.investigation import investigate
from .services.runtime_model import run_runtime_anomaly_detection, runtime_model_info
from .services.simulator import SCENARIOS, fault_bounds, inject_fault
from .services.validation import run_validation_campaign

VERSION = "3.4.0-hackathon-final"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIST = BACKEND_ROOT.parent / "frontend" / "dist"
TERMINAL_EVIDENCE_PATH = BACKEND_ROOT / "evidence" / "terminal2_snapshot.json"

SCENARIO_CATALOG = [
    {
        "id": "normal",
        "label": "Normal reference",
        "requires": [],
        "purpose": "Establish the untouched synthetic reference run.",
    },
    {
        "id": "rpm_instability",
        "label": "RPM instability",
        "requires": ["rpm"],
        "purpose": "Test sensitivity to unstable rotational behaviour.",
    },
    {
        "id": "maf_drift",
        "label": "MAF drift",
        "requires": ["maf"],
        "purpose": "Test persistent air-flow signal deviation.",
    },
    {
        "id": "load_instability",
        "label": "Engine-load instability",
        "requires": ["engine_load"],
        "purpose": "Test unstable calculated-load behaviour.",
    },
    {
        "id": "sensor_dropout",
        "label": "Sensor dropout",
        "requires": ["speed"],
        "purpose": "Test missing-data and signal-quality resilience.",
    },
    {
        "id": "signal_spikes",
        "label": "Signal spikes",
        "requires": ["speed", "rpm"],
        "purpose": "Test short-duration multichannel disturbances.",
    },
    {
        "id": "thermal_drift",
        "label": "Thermal drift",
        "requires": ["temp"],
        "purpose": "Available only when the active model declares temperature capability.",
    },
    {
        "id": "voltage_degradation",
        "label": "Voltage degradation",
        "requires": ["battery"],
        "purpose": "Available only when the active model declares battery-voltage capability.",
    },
]


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "OCTANE_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [item.strip() for item in raw.split(",") if item.strip()]


@asynccontextmanager
async def lifespan(application):
    check_config()
    if not demo_mode():
        with connection() as conn:
            if not conn.execute("SELECT 1 FROM sentinel.schema_migrations WHERE version='001_workshop'").fetchone():
                raise RuntimeError('Required database migration missing')
    yield

app = FastAPI(
    lifespan=lifespan,
    title="OctaneOS Sentinel API",
    version=VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Workshop-Id"],
)


class DemoRequest(BaseModel):
    scenario: str = "normal"
    severity: Literal["mild", "medium", "severe"] = "medium"


class ExplainRequest(BaseModel):
    analysis: dict[str, Any]
    mode: Literal["local", "fast", "deep"] = "local"


def _terminal_evidence() -> dict[str, Any]:
    try:
        return json.loads(TERMINAL_EVIDENCE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _preview_indices(length: int, regions: list[dict], max_points: int = 720) -> list[int]:
    if length <= max_points:
        return list(range(length))
    step = max(1, math.ceil(length / max_points))
    selected = set(range(0, length, step))
    selected.add(length - 1)
    for region in regions:
        for index in (region.get("start_index"), region.get("end_index")):
            if isinstance(index, int) and 0 <= index < length:
                selected.add(index)
    return sorted(selected)


def _telemetry_payload(frame, anomaly: dict) -> list[dict[str, Any]]:
    point = anomaly.get("point_scores", [0.0] * len(frame))
    components = anomaly.get("component_scores", {})
    iforest = components.get("isolation_forest", [0.0] * len(frame))
    pca = components.get("pca_reconstruction", [0.0] * len(frame))
    robust_z = components.get("robust_z", [0.0] * len(frame))
    rows: list[dict[str, Any]] = []
    normalized = frame.reset_index(drop=True)
    for index in _preview_indices(len(normalized), anomaly.get("regions", [])):
        row = normalized.iloc[index]
        rows.append(
            {
                "index": index,
                "timestamp": row.timestamp.isoformat(),
                "speed": _finite(row.speed),
                "rpm": _finite(row.rpm),
                "maf": _finite(row.maf),
                "engine_load": _finite(row.engine_load),
                "temp": _finite(row.temp),
                "fuel_rate": _finite(row.fuel_rate),
                "battery": _finite(row.battery),
                "soc": _finite(row.soc),
                "gps_fix": int(_finite(row.gps_fix) or 0),
                "anomaly_score": _finite(point[index]) if index < len(point) else 0.0,
                "iforest_score": _finite(iforest[index]) if index < len(iforest) else 0.0,
                "pca_score": _finite(pca[index]) if index < len(pca) else 0.0,
                "robust_z_score": _finite(robust_z[index]) if index < len(robust_z) else 0.0,
            }
        )
    return rows


def _signal_coverage(frame) -> dict[str, float]:
    signals = ["speed", "rpm", "maf", "engine_load", "temp", "fuel_rate", "battery", "soc"]
    return {
        signal: round(float(frame[signal].notna().mean()), 4)
        for signal in signals
        if signal in frame
    }


def _fallback_feature_importance(anomaly: dict) -> list[dict[str, Any]]:
    totals: dict[str, float] = {}
    for region in anomaly.get("regions", []):
        for rank, signal in enumerate(region.get("top_signals", [])):
            totals[signal] = totals.get(signal, 0.0) + float(region.get("score", 0.0)) / (rank + 1)
    if not totals:
        return []
    peak = max(totals.values())
    return [
        {"feature": key, "score": round(value / peak, 4)}
        for key, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:8]
    ]


def _evaluate_truth(ground_truth: dict[str, Any] | None, anomaly: dict) -> dict[str, Any] | None:
    if ground_truth is None:
        return None
    output = dict(ground_truth)
    capabilities = set(anomaly.get("capability_signals") or [])
    requirements = set(output.get("requires") or [])
    output["model_supported"] = (
        not requirements
        or requirements.issubset(capabilities)
        or not capabilities
    )
    if output.get("scenario") == "normal":
        output.update({"detected": None, "overlap_regions": 0})
        return output
    start = int(output["start_index"])
    end = int(output["end_index"])
    overlaps = [
        region
        for region in anomaly.get("regions", [])
        if int(region["end_index"]) >= start and int(region["start_index"]) <= end
    ]
    output.update({"detected": bool(overlaps), "overlap_regions": len(overlaps)})
    return output


def analyze_frame(
    frame,
    source: str,
    session_id: str,
    quality_score: int,
    analysis_ready: bool,
    quality_notes: list[str],
    file_hash: str | None = None,
    ground_truth: dict[str, Any] | None = None,
):
    anomaly = run_runtime_anomaly_detection(frame, source, session_id)
    investigation = investigate(frame, source, anomaly, quality_score)
    feature_importance = anomaly.get("feature_importance") or _fallback_feature_importance(anomaly)
    algorithms = (
        ["Isolation Forest", "PCA reconstruction", "Robust Z-score"]
        if anomaly.get("runtime_mode") == "frozen_trained_model"
        else ["Session-fitted fallback ensemble"]
    )
    return {
        "session_id": session_id,
        "source_type": source,
        "source_label": "Public VED passenger-car telemetry" if source == "ved" else "SAN-V1 telemetry",
        "sample_count": len(frame),
        "quality_score": quality_score,
        "analysis_ready": analysis_ready,
        "quality_notes": quality_notes,
        "health_score": investigation["health_score"],
        "risk": investigation["risk"],
        "anomaly_regions": anomaly["regions"],
        "feature_importance": feature_importance,
        "hypotheses": investigation["hypotheses"],
        "limitations": investigation["limitations"],
        "metrics": investigation["metrics"],
        "rules": investigation["rules"],
        "signal_coverage": _signal_coverage(frame),
        "telemetry": _telemetry_payload(frame, anomaly),
        "ground_truth": _evaluate_truth(ground_truth, anomaly),
        "model": {
            "name": anomaly["model_name"],
            "version": anomaly.get("model_version"),
            "status": anomaly["status"],
            "feature_count": len(anomaly["feature_columns"]),
            "features": anomaly["feature_columns"],
            "algorithms": algorithms,
            "contamination": anomaly.get("contamination"),
            "threshold": anomaly.get("threshold"),
            "pca_explained_variance": anomaly.get("pca_explained_variance"),
            "ensemble_weights": anomaly.get("ensemble_weights"),
            "capability_signals": anomaly.get("capability_signals") or [],
            "window_count": anomaly.get("window_count", 0),
            "anomaly_window_count": anomaly.get("anomaly_window_count", 0),
            "runtime_mode": anomaly.get("runtime_mode", "legacy_session_fit"),
            "artifact_sha256": anomaly.get("artifact_sha256"),
        },
        "provenance": {
            "sha256": file_hash,
            "pipeline": VERSION,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "raw_file_retained": False,
        },
        "claim_boundary": (
            "Behavioural anomaly screening only. Public/synthetic evidence is not Yamaha R15 V2 "
            "component-failure, remaining-useful-life, AFR, ethanol-content, ECU/DTC, injector, or ignition validation."
        ),
    }


@app.get("/health")
def health():
    model = runtime_model_info()
    return {
        "status": "ok",
        "service": "octaneos-sentinel",
        "version": VERSION,
        "frozen_model": model.get("status"),
        "frontend_built": FRONTEND_DIST.exists(),
    }


@app.get("/scenarios")
def scenarios():
    return {"scenarios": SCENARIOS, "catalog": SCENARIO_CATALOG}


@app.get("/model/info")
def model_info():
    return runtime_model_info()


@app.get("/ai/status")
def ai_status():
    return provider_status()


@app.get("/submission/status")
def submission_status():
    model = runtime_model_info()
    terminal = _terminal_evidence()
    terminal_model = terminal.get("model") or {}
    terminal_validation = terminal.get("validation") or {}
    validation = model.get("validation") or terminal_validation
    current_runtime_verified = bool(model.get("available"))
    return {
        "project": "OctaneOS Sentinel V3",
        "team": "Asphalt Sovereign",
        "build": VERSION,
        "event": {
            "name": "Innovation Hacks Global AI Hackathon 2026",
            "submission_deadline": "2026-09-10T23:23:00+05:30",
            "platform": "Unstop",
            "round": "Project Submission",
        },
        "evidence": {
            "frozen_model_available": current_runtime_verified,
            "model_version": model.get("model_version") or terminal_model.get("model_version"),
            "artifact_sha256": model.get("artifact_sha256") or terminal_model.get("artifact_sha256"),
            "untouched_normal_fpr": validation.get("untouched_normal_fpr"),
            "controlled_injection_run_detection_rate": validation.get("injected_run_detection_rate"),
            "controlled_injection_experiments": validation.get("injected_run_experiments"),
            "controlled_injection_detected": validation.get("injected_run_detected"),
            "source": "current frozen runtime" if current_runtime_verified else terminal.get("source"),
            "current_runtime_verified": current_runtime_verified,
        },
        "verification": terminal.get("verification") or {},
        "submission_items": [
            {"item": "Source code", "status": "ready"},
            {"item": "README and reproducibility guide", "status": "ready"},
            {"item": "Presentation", "status": "ready in submission bundle"},
            {"item": "3-5 minute demo video", "status": "recording required"},
            {"item": "Project description", "status": "ready"},
            {"item": "Deployment link", "status": "optional; deploy or show local build"},
        ],
        "truth_boundary": (
            "Controlled perturbations measure anomaly sensitivity, not real-world component-failure accuracy."
        ),
    }


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    try:
        if file.filename and not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=415, detail="Upload a CSV telemetry file.")
        raw = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="CSV exceeds the 20 MB demo limit.")
        session = ingest_csv_bytes(raw)
        if not session.analysis_ready:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Session failed analysis-readiness gate",
                    "quality_score": session.quality_score,
                    "notes": session.quality_notes,
                },
            )
        return analyze_frame(
            session.frame,
            session.source_type,
            session.session_id,
            session.quality_score,
            session.analysis_ready,
            session.quality_notes,
            session.file_hash,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/demo")
def demo(request: DemoRequest):
    try:
        if request.scenario not in SCENARIOS:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown scenario. Choose one of: {', '.join(SCENARIOS)}",
            )
        frame = demo_frame()
        catalog = next(item for item in SCENARIO_CATALOG if item["id"] == request.scenario)
        if request.scenario == "normal":
            truth = {
                "scenario": "normal",
                "severity": request.severity,
                "start_index": None,
                "end_index": None,
                "requires": [],
                "label_hidden_from_model": True,
            }
        else:
            start, end = fault_bounds(len(frame))
            truth = {
                "scenario": request.scenario,
                "severity": request.severity,
                "start_index": start,
                "end_index": end,
                "requires": catalog["requires"],
                "label_hidden_from_model": True,
            }
        modified = inject_fault(frame, request.scenario, severity=request.severity)
        return analyze_frame(
            modified,
            "ved",
            f"DEMO-{request.scenario.upper()}-{request.severity.upper()}",
            98,
            True,
            [
                "Synthetic controlled session for deterministic hackathon validation; not real vehicle evidence."
            ],
            None,
            truth,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/explain")
async def explain(request: ExplainRequest):
    return await explain_analysis(request.analysis, request.mode)


@app.get("/model/validate")
def model_validate(repeats: int = 4):
    return run_validation_campaign(max(1, min(repeats, 20)))


@app.exception_handler(404)
async def not_found(_, __):
    if FRONTEND_DIST.exists():
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return JSONResponse(status_code=404, content={"detail": "Resource not found"})
    return JSONResponse(status_code=404, content={"detail": "Resource not found"})


from .workshop.api import router as workshop_router
app.include_router(workshop_router)
from .workshop.security import WorkshopBoundary
app.add_middleware(WorkshopBoundary)

if FRONTEND_DIST.exists():
    # Register last so every API route above wins before the single-page application.
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
