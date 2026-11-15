from __future__ import annotations

from collections import Counter
from functools import lru_cache
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from .anomaly import run_anomaly_detection
from .model_store import ModelIntegrityError, load_bundle
from .training import score_with_trained_model
from .windowing import build_window_matrix

load_dotenv()

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_MODEL_DIR = BACKEND_ROOT / "artifacts" / "sentinel_submission_frozen"
KNOWN_SIGNALS = ("speed", "rpm", "maf", "engine_load", "temp", "fuel_rate", "battery", "soc")


def runtime_model_dir() -> Path:
    raw = os.getenv("OCTANE_MODEL_DIR", "").strip()
    if not raw:
        return DEFAULT_RUNTIME_MODEL_DIR
    path = Path(raw)
    return path if path.is_absolute() else (BACKEND_ROOT / path)


@lru_cache(maxsize=4)
def _cached_load(path_text: str):
    return load_bundle(Path(path_text))


def clear_runtime_cache() -> None:
    _cached_load.cache_clear()


def _display_model_path(path: Path) -> str:
    """Return a portable path without exposing a developer workstation username."""
    try:
        return str(path.resolve().relative_to(BACKEND_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return path.name


def _feature_signals(name: str) -> list[str]:
    for signal in KNOWN_SIGNALS:
        if name.startswith(f"{signal}__"):
            return [signal]
    if name.startswith("corr__"):
        return [s for s in KNOWN_SIGNALS if s in name]
    if name.startswith("dynamics__"):
        return ["speed"]
    return []


def _window_signal_contributions(feature_df: pd.DataFrame, bundle: dict[str, Any]) -> list[list[str]]:
    cols = list(bundle["feature_columns"])
    x = feature_df.reindex(columns=cols).replace([np.inf, -np.inf], np.nan)
    x = x.fillna(pd.Series(bundle["fill_values"]))
    scaled = bundle["scaler"].transform(x.to_numpy(dtype=float))
    center = np.asarray(bundle["robust_center"], dtype=float)
    scale = np.maximum(np.asarray(bundle["robust_scale"], dtype=float), 1e-6)
    deviation = np.abs((scaled - center) / scale)

    allowed_signals = set(bundle.get("capability_signals", []))

    output: list[list[str]] = []
    for row in deviation:
        scores: Counter[str] = Counter()
        for idx, value in enumerate(row):
            if not np.isfinite(value):
                continue
            for signal in _feature_signals(cols[idx]):
                # Never surface a dominant contributor for a signal family that the
                # frozen model does not claim as a validated capability. Coverage-only
                # features for sparse temp/battery/SOC channels must not become a
                # diagnostic hypothesis on the public powertrain model.
                if allowed_signals and signal not in allowed_signals:
                    continue
                scores[signal] += float(value)
        output.append([name for name, _ in scores.most_common(5)])
    return output


def _merge_regions(windows: list[dict], top_signals: list[list[str]]) -> list[dict]:
    flagged = [(i, w) for i, w in enumerate(windows) if w.get("is_anomaly")]
    if not flagged:
        return []

    regions: list[dict] = []
    current: dict[str, Any] | None = None
    signal_counts: Counter[str] = Counter()
    for idx, w in flagged:
        if current is None or int(w["start_index"]) > int(current["end_index"]) + 1:
            if current is not None:
                current["top_signals"] = [s for s, _ in signal_counts.most_common(5)]
                regions.append(current)
            current = {
                "start_index": int(w["start_index"]),
                "end_index": int(w["end_index"]),
                "start_time": w["start_time"],
                "end_time": w["end_time"],
                "score": float(w["score"]),
                "mean_score": float(w["score"]),
                "duration_samples": int(w["end_index"] - w["start_index"] + 1),
                "window_count": 1,
                "component_scores": {
                    key: float(value)
                    for key, value in w.get("components", {}).items()
                },
            }
            signal_counts = Counter(top_signals[idx])
        else:
            assert current is not None
            current["end_index"] = max(int(current["end_index"]), int(w["end_index"]))
            current["end_time"] = w["end_time"]
            current["score"] = max(float(current["score"]), float(w["score"]))
            current["window_count"] += 1
            n = current["window_count"]
            current["mean_score"] = ((float(current["mean_score"]) * (n - 1)) + float(w["score"])) / n
            current["duration_samples"] = int(current["end_index"] - current["start_index"] + 1)
            for key, value in w.get("components", {}).items():
                current["component_scores"][key] = max(
                    float(current["component_scores"].get(key, 0.0)),
                    float(value),
                )
            signal_counts.update(top_signals[idx])

    if current is not None:
        current["top_signals"] = [s for s, _ in signal_counts.most_common(5)]
        regions.append(current)

    return sorted(regions, key=lambda r: r["score"], reverse=True)[:20]


def _feature_importance(windows: list[dict], top_signals: list[list[str]]) -> list[dict[str, Any]]:
    """Aggregate ranked, capability-filtered contributors for UI explanation only."""
    totals: Counter[str] = Counter()
    for window, signals in zip(windows, top_signals):
        if not window.get("is_anomaly"):
            continue
        weight = max(float(window.get("score", 0.0)), 0.01)
        for rank, signal in enumerate(signals):
            totals[signal] += weight / (rank + 1)
    if not totals:
        return []
    peak = max(totals.values())
    return [
        {"feature": signal, "score": round(float(value / peak), 4)}
        for signal, value in totals.most_common(8)
    ]


def _sample_scores(frame_len: int, windows: list[dict], component: str | None = None) -> list[float]:
    out = np.zeros(frame_len, dtype=float)
    for w in windows:
        value = float(w["score"] if component is None else w.get("components", {}).get(component, 0.0))
        start = max(0, int(w["start_index"]))
        end = min(frame_len - 1, int(w["end_index"]))
        if end >= start:
            out[start : end + 1] = np.maximum(out[start : end + 1], value)
    return [float(x) for x in out]


def run_runtime_anomaly_detection(frame: pd.DataFrame, source: str, session_id: str) -> dict[str, Any]:
    # The frozen public VED model is not applied to SAN/motorcycle data until a dedicated
    # SAN-trained capability model exists.
    if source != "ved":
        legacy = run_anomaly_detection(frame)
        legacy["runtime_mode"] = "legacy_capability_fallback"
        legacy["runtime_note"] = "Frozen public VED powertrain model is not valid for SAN telemetry."
        return legacy

    path = runtime_model_dir()
    try:
        bundle, manifest = _cached_load(str(path.resolve()))
    except FileNotFoundError:
        legacy = run_anomaly_detection(frame)
        legacy["runtime_mode"] = "legacy_fallback_no_frozen_model"
        legacy["runtime_note"] = f"Frozen trained model not found at {path}."
        return legacy
    except ModelIntegrityError as exc:
        legacy = run_anomaly_detection(frame)
        legacy["runtime_mode"] = "legacy_fallback_invalid_frozen_model"
        legacy["runtime_note"] = str(exc)
        return legacy
    except Exception:
        legacy = run_anomaly_detection(frame)
        legacy["runtime_mode"] = "legacy_fallback_unreadable_frozen_model"
        legacy["runtime_note"] = "Frozen model could not be loaded safely."
        return legacy

    feature_df, _ = build_window_matrix(
        frame,
        session_id=session_id,
        window_size=int(bundle["window_size"]),
        stride=int(bundle["stride"]),
    )
    scored = score_with_trained_model(frame, session_id, bundle)
    windows = scored.get("windows", [])
    tops = _window_signal_contributions(feature_df, bundle) if not feature_df.empty else [[] for _ in windows]
    regions = _merge_regions(windows, tops)

    return {
        "regions": regions,
        "point_scores": _sample_scores(len(frame), windows),
        "component_scores": {
            "isolation_forest": _sample_scores(len(frame), windows, "isolation_forest"),
            "pca_reconstruction": _sample_scores(len(frame), windows, "pca_reconstruction"),
            "robust_z": _sample_scores(len(frame), windows, "robust_z"),
        },
        "feature_importance": _feature_importance(windows, tops),
        "feature_columns": list(bundle.get("feature_columns", [])),
        "model_name": "Sentinel Frozen Powertrain Ensemble",
        "model_version": manifest.get("model_version", bundle.get("model_version")),
        "status": scored.get("status", "ok"),
        "threshold": scored.get("threshold"),
        "ensemble_weights": scored.get("ensemble_weights", bundle.get("ensemble_weights", {})),
        "capability_signals": scored.get("capability_signals", bundle.get("capability_signals", [])),
        "window_count": scored.get("window_count", 0),
        "anomaly_window_count": scored.get("anomaly_window_count", 0),
        "pca_explained_variance": manifest.get("pca_explained_variance"),
        "artifact_sha256": manifest.get("artifact_sha256"),
        "runtime_mode": "frozen_trained_model",
        "runtime_model_dir": _display_model_path(path),
    }


def runtime_model_info() -> dict[str, Any]:
    path = runtime_model_dir()
    try:
        _, manifest = _cached_load(str(path.resolve()))
    except FileNotFoundError:
        return {
            "available": False,
            "model_dir": _display_model_path(path),
            "status": "missing",
            "fallback_available": True,
        }
    except ModelIntegrityError as exc:
        return {
            "available": False,
            "model_dir": _display_model_path(path),
            "status": "integrity_failed",
            "fallback_available": True,
            "reason": str(exc),
        }
    except Exception:
        return {
            "available": False,
            "model_dir": _display_model_path(path),
            "status": "unreadable",
            "fallback_available": True,
            "reason": "Frozen model could not be loaded safely.",
        }

    validation_path = path / "final_test_report.json"
    validation: dict[str, Any] | None = None
    if validation_path.exists():
        try:
            report = json.loads(validation_path.read_text(encoding="utf-8"))
            normal = report.get("untouched_normal") or {}
            window = report.get("controlled_injection_window_level") or {}
            run = report.get("controlled_injection_run_level") or {}
            validation = {
                # V3.2/V3.3 reports use nested metric groups. Keep backward-compatible
                # fallbacks so older experimental reports still render in Model Lab.
                "untouched_normal_fpr": report.get("untouched_normal_fpr", normal.get("false_positive_rate")),
                "injected_window_precision": report.get("injected_window_precision", window.get("precision")),
                "injected_window_recall": report.get("injected_window_recall", window.get("recall_detection_rate")),
                "injected_window_f1": report.get("injected_window_f1", window.get("f1")),
                "injected_run_detection_rate": report.get("injected_run_detection_rate", run.get("detection_rate")),
                "injected_run_experiments": run.get("experiments"),
                "injected_run_detected": run.get("detected_experiments"),
                "severity": report.get("severity") or report.get("severity_results"),
                "scenario_results": report.get("scenario_results"),
                "detector_results": report.get("detector_results"),
                "claim_boundary": report.get("claim_boundary") or report.get("validation_policy"),
            }
        except Exception:
            validation = {"status": "report_unreadable"}

    return {
        "available": True,
        "status": "frozen",
        "model_dir": _display_model_path(path),
        "model_version": manifest.get("model_version"),
        "artifact_sha256": manifest.get("artifact_sha256"),
        "feature_count": manifest.get("feature_count"),
        "capability_signals": manifest.get("capability_signals"),
        "training_vehicles": manifest.get("training_vehicles"),
        "calibration_vehicles": manifest.get("calibration_vehicles"),
        "test_vehicles": manifest.get("test_vehicles"),
        "decision_threshold": manifest.get("decision_threshold"),
        "ensemble_weights": manifest.get("ensemble_weights"),
        "algorithms": ["Isolation Forest", "PCA reconstruction", "Robust Z-score"],
        "domain_boundary": manifest.get("domain_boundary"),
        "claim_boundary": manifest.get("claim_boundary"),
        "validation": validation,
    }
