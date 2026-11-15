from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from itertools import product
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from .model_store import save_bundle
from .simulator import fault_bounds, inject_fault
from .windowing import combine_window_matrices, build_window_matrix

MODEL_VERSION = "sentinel-powertrain-baseline-0.6"
DETECTOR_NAMES = ("isolation_forest", "pca_reconstruction", "robust_z")
DEFAULT_ENSEMBLE_WEIGHTS = {"iforest": 0.48, "pca": 0.32, "robust_z": 0.20}
CORE_CALIBRATION_SCENARIOS = ("rpm_instability", "maf_drift", "load_instability", "sensor_dropout", "signal_spikes")
CALIBRATION_SEVERITIES = ("medium", "severe")


@dataclass
class TrainingSession:
    session_id: str
    vehicle_id: str
    frame: pd.DataFrame
    source_hash: str | None = None


def _quantile_scale(values: np.ndarray, low: float, high: float) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    denom = max(high - low, 1e-9)
    return np.clip((values - low) / denom, 0.0, 1.0)


def _hash_frame(frame: pd.DataFrame) -> str:
    raw = frame.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _split_groups(groups: np.ndarray, calibration_fraction: float, test_fraction: float, random_state: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    unique = np.array(sorted(pd.Series(groups).astype(str).unique().tolist()), dtype=object)
    if len(unique) < 3:
        raise ValueError("At least 3 distinct vehicles/sessions are required for train/calibration/test separation.")
    rng = np.random.default_rng(random_state)
    rng.shuffle(unique)
    n = len(unique)
    n_test = max(1, int(round(n * test_fraction)))
    n_cal = max(1, int(round(n * calibration_fraction)))
    if n_test + n_cal >= n:
        n_test = 1
        n_cal = 1
    test_groups = set(unique[:n_test])
    cal_groups = set(unique[n_test : n_test + n_cal])
    train_groups = set(unique[n_test + n_cal :])
    as_str = pd.Series(groups).astype(str).to_numpy()
    train_idx = np.flatnonzero(np.isin(as_str, list(train_groups)))
    cal_idx = np.flatnonzero(np.isin(as_str, list(cal_groups)))
    test_idx = np.flatnonzero(np.isin(as_str, list(test_groups)))
    return train_idx, cal_idx, test_idx


def _prepare_matrix(feature_df: pd.DataFrame, train_idx: np.ndarray, feature_columns: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    numeric = feature_df.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)
    if feature_columns is None:
        train_numeric = numeric.iloc[train_idx]
        coverage = train_numeric.notna().mean()
        variability = train_numeric.nunique(dropna=True)
        feature_columns = [c for c in numeric.columns if coverage.get(c, 0) >= 0.60 and variability.get(c, 0) > 1]
    return numeric.reindex(columns=feature_columns), feature_columns


def _fit_fill_values(x: pd.DataFrame) -> pd.Series:
    return x.median(numeric_only=True).fillna(0.0)


def _raw_detector_scores(bundle: dict, x_df: pd.DataFrame) -> dict[str, np.ndarray]:
    cols = bundle["feature_columns"]
    x = x_df.reindex(columns=cols).replace([np.inf, -np.inf], np.nan)
    x = x.fillna(pd.Series(bundle["fill_values"]))
    scaled = bundle["scaler"].transform(x.to_numpy(dtype=float))

    raw_if = -bundle["iforest"].score_samples(scaled)
    reduced = bundle["pca"].transform(scaled)
    reconstructed = bundle["pca"].inverse_transform(reduced)
    raw_pca = np.mean((scaled - reconstructed) ** 2, axis=1)
    center = np.asarray(bundle["robust_center"], dtype=float)
    scale = np.asarray(bundle["robust_scale"], dtype=float)
    raw_z = np.max(np.abs((scaled - center) / np.maximum(scale, 1e-6)), axis=1)
    return {"isolation_forest": raw_if, "pca_reconstruction": raw_pca, "robust_z": raw_z}


def _normalized_detector_scores(bundle: dict, x_df: pd.DataFrame) -> dict[str, np.ndarray]:
    raw = _raw_detector_scores(bundle, x_df)
    cal = bundle["score_normalization"]
    return {
        "isolation_forest": _quantile_scale(raw["isolation_forest"], cal["iforest_low"], cal["iforest_high"]),
        "pca_reconstruction": _quantile_scale(raw["pca_reconstruction"], cal["pca_low"], cal["pca_high"]),
        "robust_z": _quantile_scale(raw["robust_z"], cal["z_low"], cal["z_high"]),
    }


def _ensemble_from_components(components: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    return (
        float(weights["iforest"]) * components["isolation_forest"]
        + float(weights["pca"]) * components["pca_reconstruction"]
        + float(weights["robust_z"]) * components["robust_z"]
    )


def _score_static(bundle: dict, x_df: pd.DataFrame) -> dict[str, np.ndarray]:
    components = _normalized_detector_scores(bundle, x_df)
    ensemble = _ensemble_from_components(components, bundle["ensemble_weights"])
    return {**components, "ensemble": ensemble}


def _capability_signals(feature_columns: list[str]) -> list[str]:
    signals = []
    for signal in ["speed", "rpm", "maf", "engine_load", "temp", "fuel_rate", "battery", "soc"]:
        prefix = f"{signal}__"
        dynamic = [c for c in feature_columns if c.startswith(prefix) and not c.endswith("__coverage")]
        if dynamic:
            signals.append(signal)
    return signals


def _scenario_supported(capabilities: set[str], scenario: str) -> bool:
    requirements = {
        "rpm_instability": {"rpm"},
        "maf_drift": {"maf"},
        "load_instability": {"engine_load"},
        "sensor_dropout": {"speed"},
        "signal_spikes": {"speed"},
        "thermal_drift": {"temp"},
        "voltage_degradation": {"battery"},
    }
    return requirements.get(scenario, set()).issubset(capabilities)


def _window_truth(meta, truth_start: int, truth_end: int, min_overlap_fraction: float = 0.50) -> np.ndarray:
    labels = []
    for m in meta:
        overlap = max(0, min(m.end_index, truth_end) - max(m.start_index, truth_start) + 1)
        length = max(1, m.end_index - m.start_index + 1)
        labels.append(overlap / length >= min_overlap_fraction)
    return np.asarray(labels, dtype=bool)


def _frame_components(frame: pd.DataFrame, session_id: str, bundle: dict) -> tuple[dict[str, np.ndarray], list]:
    matrix, meta = build_window_matrix(
        frame,
        session_id=session_id,
        window_size=int(bundle["window_size"]),
        stride=int(bundle["stride"]),
    )
    if matrix.empty:
        return {k: np.array([], dtype=float) for k in DETECTOR_NAMES}, []
    return _normalized_detector_scores(bundle, matrix), meta


def _weight_grid() -> list[dict[str, float]]:
    # V3.3 permits a detector to receive zero weight when calibration shows that
    # it harms generalisation. At least two detectors must remain active so the
    # production score is still a genuine ensemble rather than a renamed single model.
    out = []
    grid = np.arange(0.0, 1.01, 0.1)
    for a in grid:
        for b in grid:
            c = round(1.0 - a - b, 10)
            if c < -1e-9 or c > 1.0 + 1e-9:
                continue
            vals = [float(round(a, 2)), float(round(b, 2)), float(round(max(c, 0.0), 2))]
            if sum(v > 0.0 for v in vals) < 2:
                continue
            out.append({"iforest": vals[0], "pca": vals[1], "robust_z": vals[2]})
    out.append(DEFAULT_ENSEMBLE_WEIGHTS.copy())
    seen = set(); dedup = []
    for w in out:
        key = (w["iforest"], w["pca"], w["robust_z"])
        if key not in seen:
            seen.add(key); dedup.append(w)
    return dedup


def _session_guard_threshold(score_arrays: list[np.ndarray], target_fpr: float, guard_quantile: float) -> float:
    """Choose a conservative threshold from per-session normal score envelopes.

    Pooling every calibration window lets long/easy sessions dominate the threshold.
    V3.3 instead computes each session's (1-target_fpr) quantile and guards against
    vehicle heterogeneity by taking a high quantile of those session thresholds.
    """
    valid = [np.asarray(a, dtype=float) for a in score_arrays if len(a)]
    if not valid:
        raise ValueError("No calibration normal score arrays were available.")
    per_session = np.asarray([np.quantile(a, 1.0 - target_fpr) for a in valid], dtype=float)
    return float(np.quantile(per_session, guard_quantile))


def _calibrate_ensemble(
    bundle: dict,
    calibration_sessions: list[TrainingSession],
    target_normal_fpr: float = 0.02,
    guard_quantile: float = 0.90,
) -> dict:
    capabilities = set(bundle["capability_signals"])
    normal_by_session: dict[str, dict[str, np.ndarray]] = {}
    positive_experiments: list[dict[str, np.ndarray]] = []

    for session in calibration_sessions:
        comps, _ = _frame_components(session.frame, session.session_id + "-cal-normal", bundle)
        if all(len(comps[k]) for k in DETECTOR_NAMES):
            normal_by_session[session.session_id] = {k: comps[k] for k in DETECTOR_NAMES}

        for scenario in CORE_CALIBRATION_SCENARIOS:
            if not _scenario_supported(capabilities, scenario):
                continue
            for severity in CALIBRATION_SEVERITIES:
                try:
                    faulted = inject_fault(session.frame, scenario, severity=severity)
                except ValueError:
                    continue
                comps_f, meta_f = _frame_components(
                    faulted, f"{session.session_id}-{scenario}-{severity}-cal", bundle
                )
                if not meta_f:
                    continue
                start, end = fault_bounds(len(faulted))
                truth = _window_truth(meta_f, start, end, min_overlap_fraction=0.50)
                if not truth.any():
                    continue
                positive_experiments.append({k: comps_f[k][truth] for k in DETECTOR_NAMES})

    if len(normal_by_session) < 1:
        raise ValueError("Calibration partition produced no usable normal sessions.")

    pooled_normal = {
        k: np.concatenate([v[k] for v in normal_by_session.values()]) for k in DETECTOR_NAMES
    }
    pooled_positive = {
        k: np.concatenate([e[k] for e in positive_experiments]) if positive_experiments else np.array([], dtype=float)
        for k in DETECTOR_NAMES
    }

    detector_thresholds = {}
    detector_calibration = {}
    for k in DETECTOR_NAMES:
        arrays = [v[k] for v in normal_by_session.values()]
        threshold = _session_guard_threshold(arrays, target_normal_fpr, guard_quantile)
        detector_thresholds[k] = threshold
        pooled_fpr = float(np.mean(pooled_normal[k] >= threshold))
        session_fprs = [float(np.mean(a >= threshold)) for a in arrays]
        detector_calibration[k] = {
            "threshold": threshold,
            "pooled_normal_fpr": pooled_fpr,
            "session_fpr_p90": float(np.quantile(session_fprs, 0.90)),
            "injected_positive_recall": float(np.mean(pooled_positive[k] >= threshold)) if len(pooled_positive[k]) else None,
        }

    best = None
    for weights in _weight_grid():
        normal_arrays = [
            _ensemble_from_components(v, weights) for v in normal_by_session.values()
        ]
        threshold = _session_guard_threshold(normal_arrays, target_normal_fpr, guard_quantile)
        n_score = np.concatenate(normal_arrays)
        fpr = float(np.mean(n_score >= threshold))
        session_fprs = [float(np.mean(a >= threshold)) for a in normal_arrays]

        if positive_experiments:
            exp_scores = [_ensemble_from_components(e, weights) for e in positive_experiments]
            p_score = np.concatenate(exp_scores)
            window_recall = float(np.mean(p_score >= threshold))
            run_detection = float(np.mean([np.any(a >= threshold) for a in exp_scores]))
        else:
            window_recall = 0.0
            run_detection = 0.0

        # Product objective: detect abnormal runs while keeping conservative normal behaviour.
        # The session guard already limits FPR; penalties discourage any weight set that
        # exceeds the requested pooled or per-session envelope.
        session_p90 = float(np.quantile(session_fprs, 0.90))
        fpr_penalty = 2.0 * max(0.0, fpr - target_normal_fpr)
        session_penalty = 1.0 * max(0.0, session_p90 - max(target_normal_fpr * 1.5, 0.03))
        objective = 0.72 * run_detection + 0.28 * window_recall - fpr_penalty - session_penalty
        candidate = {
            "weights": weights,
            "threshold": threshold,
            "normal_fpr": fpr,
            "session_fpr_p90": session_p90,
            "injected_positive_recall": window_recall,
            "injected_run_detection_rate": run_detection,
            "objective": objective,
        }
        if best is None or candidate["objective"] > best["objective"] + 1e-12:
            best = candidate

    assert best is not None
    return {
        "target_normal_fpr": target_normal_fpr,
        "guard_quantile": guard_quantile,
        "normal_sessions": int(len(normal_by_session)),
        "normal_windows": int(len(pooled_normal["isolation_forest"])),
        "injected_positive_windows": int(len(pooled_positive["isolation_forest"])),
        "injected_experiments": int(len(positive_experiments)),
        "chosen_weights": best["weights"],
        "decision_threshold": float(best["threshold"]),
        "calibration_normal_fpr": float(best["normal_fpr"]),
        "calibration_session_fpr_p90": float(best["session_fpr_p90"]),
        "calibration_injected_positive_recall": float(best["injected_positive_recall"]),
        "calibration_injected_run_detection_rate": float(best["injected_run_detection_rate"]),
        "detector_thresholds": detector_thresholds,
        "detector_calibration": detector_calibration,
        "policy": "V3.3 uses session-robust calibration: per-session normal score envelopes, conservative cross-session guard quantile, and medium/severe controlled perturbations. Final-test vehicles are excluded from fitting and calibration.",
    }


def train_baseline_model(
    sessions: Iterable[TrainingSession],
    output_dir: str | Path | None = None,
    window_size: int = 16,
    stride: int = 8,
    calibration_fraction: float = 0.15,
    test_fraction: float = 0.15,
    random_state: int = 20260909,
    target_normal_fpr: float = 0.02,
    calibration_guard_quantile: float = 0.90,
) -> dict:
    sessions = list(sessions)
    if len(sessions) < 6:
        raise ValueError("At least 6 quality-approved sessions are required for train/calibration/test training.")

    feature_df, meta_df = combine_window_matrices(
        [(s.session_id, s.frame) for s in sessions], window_size=window_size, stride=stride
    )
    if len(feature_df) < 30:
        raise ValueError("Training requires at least 30 telemetry windows after quality filtering.")

    session_to_vehicle = {s.session_id: s.vehicle_id for s in sessions}
    meta_df["vehicle_id"] = meta_df.session_id.map(session_to_vehicle)
    groups = meta_df["vehicle_id"].astype(str).to_numpy()
    if pd.Series(groups).nunique() < 3:
        groups = meta_df["session_id"].astype(str).to_numpy()

    train_idx, cal_idx, test_idx = _split_groups(groups, calibration_fraction, test_fraction, random_state)

    x_all, feature_columns = _prepare_matrix(feature_df, train_idx=train_idx)
    if len(feature_columns) < 8:
        raise ValueError("Fewer than 8 stable features survived the training-only quality gate.")

    fill = _fit_fill_values(x_all.iloc[train_idx])
    x_train = x_all.iloc[train_idx].fillna(fill).to_numpy(dtype=float)
    scaler = RobustScaler(quantile_range=(10, 90))
    train_scaled = scaler.fit_transform(x_train)

    iforest = IsolationForest(
        n_estimators=520,
        contamination="auto",
        max_samples="auto",
        random_state=random_state,
        n_jobs=-1,
    ).fit(train_scaled)

    max_components = max(1, min(14, train_scaled.shape[1], train_scaled.shape[0] - 1))
    pca = PCA(n_components=max_components, random_state=random_state).fit(train_scaled)
    robust_center = np.median(train_scaled, axis=0)
    q75 = np.percentile(train_scaled, 75, axis=0)
    q25 = np.percentile(train_scaled, 25, axis=0)
    robust_scale = np.maximum(q75 - q25, 1e-6)

    # Score normalization is fitted only from the training partition.
    tmp_bundle = {
        "feature_columns": feature_columns,
        "fill_values": fill.to_dict(),
        "scaler": scaler,
        "iforest": iforest,
        "pca": pca,
        "robust_center": robust_center,
        "robust_scale": robust_scale,
    }
    raw_train = _raw_detector_scores(tmp_bundle, x_all.iloc[train_idx])
    score_normalization = {
        "iforest_low": float(np.quantile(raw_train["isolation_forest"], 0.50)),
        "iforest_high": float(np.quantile(raw_train["isolation_forest"], 0.995)),
        "pca_low": float(np.quantile(raw_train["pca_reconstruction"], 0.50)),
        "pca_high": float(np.quantile(raw_train["pca_reconstruction"], 0.995)),
        "z_low": float(np.quantile(raw_train["robust_z"], 0.50)),
        "z_high": float(np.quantile(raw_train["robust_z"], 0.995)),
    }

    capabilities = _capability_signals(feature_columns)
    bundle = {
        "model_version": MODEL_VERSION,
        "feature_columns": feature_columns,
        "fill_values": fill.to_dict(),
        "scaler": scaler,
        "iforest": iforest,
        "pca": pca,
        "robust_center": robust_center,
        "robust_scale": robust_scale,
        "score_normalization": score_normalization,
        "window_size": window_size,
        "stride": stride,
        "capability_signals": capabilities,
        "truth_overlap_fraction": 0.50,
    }

    train_session_ids = sorted(meta_df.iloc[train_idx].session_id.unique().tolist())
    cal_session_ids = sorted(meta_df.iloc[cal_idx].session_id.unique().tolist())
    test_session_ids = sorted(meta_df.iloc[test_idx].session_id.unique().tolist())
    train_vehicle_ids = sorted(meta_df.iloc[train_idx].vehicle_id.unique().tolist())
    cal_vehicle_ids = sorted(meta_df.iloc[cal_idx].vehicle_id.unique().tolist())
    test_vehicle_ids = sorted(meta_df.iloc[test_idx].vehicle_id.unique().tolist())

    by_id = {s.session_id: s for s in sessions}
    calibration_sessions = [by_id[sid] for sid in cal_session_ids if sid in by_id]
    calibration_report = _calibrate_ensemble(
        bundle, calibration_sessions, target_normal_fpr=target_normal_fpr, guard_quantile=calibration_guard_quantile
    )
    bundle["ensemble_weights"] = calibration_report["chosen_weights"]
    bundle["threshold"] = calibration_report["decision_threshold"]
    bundle["detector_thresholds"] = calibration_report["detector_thresholds"]

    source_hashes = [{
        "session_id": s.session_id,
        "vehicle_id": s.vehicle_id,
        "sha256": s.source_hash or _hash_frame(s.frame),
    } for s in sessions]

    manifest = {
        "model_version": MODEL_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Capability-aware unsupervised powertrain-behaviour ensemble for abnormal telemetry-window detection.",
        "required_signal_family": ["speed", "rpm", "maf_or_engine_load"],
        "capability_signals": capabilities,
        "domain_boundary": "Public passenger-car telemetry baseline; not a Yamaha R15 component-failure or remaining-useful-life model.",
        "training_sessions": len(train_session_ids),
        "calibration_sessions": len(cal_session_ids),
        "test_sessions": len(test_session_ids),
        "training_vehicles": len(train_vehicle_ids),
        "calibration_vehicles": len(cal_vehicle_ids),
        "test_vehicles": len(test_vehicle_ids),
        "training_windows": int(len(train_idx)),
        "calibration_windows": int(len(cal_idx)),
        "test_windows": int(len(test_idx)),
        "train_session_ids": train_session_ids,
        "calibration_session_ids": cal_session_ids,
        "test_session_ids": test_session_ids,
        "train_vehicle_ids": train_vehicle_ids,
        "calibration_vehicle_ids": cal_vehicle_ids,
        "test_vehicle_ids": test_vehicle_ids,
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "window_size_samples": window_size,
        "stride_samples": stride,
        "truth_overlap_fraction": 0.50,
        "split_strategy": "V3.3 deterministic group split by vehicle_id using a new lockbox seed: training / calibration / final test. No vehicle appears in more than one partition.",
        "decision_threshold": bundle["threshold"],
        "ensemble_weights": bundle["ensemble_weights"],
        "detector_thresholds": bundle["detector_thresholds"],
        "pca_explained_variance": float(np.sum(pca.explained_variance_ratio_)),
        "calibration": calibration_report,
        "sources": source_hashes,
        "claim_boundary": "Calibration uses controlled perturbations only on calibration vehicles. V3.3 final metrics come from a new vehicle-level holdout created with the V3.3 split seed; synthetic perturbation metrics do not establish real-world component-failure accuracy.",
    }
    paths = save_bundle(bundle, manifest, output_dir)
    return {**manifest, "artifact_paths": paths}


def score_with_trained_model(frame: pd.DataFrame, session_id: str, bundle: dict) -> dict:
    feature_df, meta = build_window_matrix(
        frame,
        session_id=session_id,
        window_size=int(bundle["window_size"]),
        stride=int(bundle["stride"]),
    )
    if feature_df.empty:
        return {"status": "insufficient_windows", "windows": [], "threshold": bundle.get("threshold")}
    scores = _score_static(bundle, feature_df)
    ensemble = scores["ensemble"]
    threshold = float(bundle["threshold"])
    detector_thresholds = bundle.get("detector_thresholds", {})
    windows = []
    for i, m in enumerate(meta):
        components = {k: float(scores[k][i]) for k in DETECTOR_NAMES}
        detector_flags = {k: bool(components[k] >= float(detector_thresholds.get(k, 1.1))) for k in DETECTOR_NAMES}
        windows.append({
            **m.__dict__,
            "score": float(ensemble[i]),
            "is_anomaly": bool(ensemble[i] >= threshold),
            "components": components,
            "detector_flags": detector_flags,
        })
    return {
        "status": "ok",
        "model_version": bundle["model_version"],
        "threshold": threshold,
        "ensemble_weights": bundle["ensemble_weights"],
        "capability_signals": bundle.get("capability_signals", []),
        "window_count": len(windows),
        "anomaly_window_count": int(sum(w["is_anomaly"] for w in windows)),
        "windows": windows,
    }
