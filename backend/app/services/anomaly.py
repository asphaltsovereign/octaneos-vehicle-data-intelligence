from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from .features import engineer_features, model_matrix


def _normalize(raw: np.ndarray) -> np.ndarray:
    raw = np.asarray(raw, dtype=float)
    if raw.size == 0:
        return raw
    lo, hi = np.nanpercentile(raw, 5), np.nanpercentile(raw, 95)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-12:
        return np.zeros_like(raw)
    return np.clip((raw - lo) / (hi - lo), 0, 1)


def _robust_z(scaled: np.ndarray) -> np.ndarray:
    return _normalize(np.nanmax(np.abs(scaled), axis=1))


def _ewma_cusum_signal(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Collapse multivariate deviation into one robust magnitude series.
    magnitude = np.nanmean(np.abs(matrix), axis=1)
    alpha = 0.18
    ewma = np.zeros_like(magnitude)
    ewma[0] = magnitude[0]
    for i in range(1, len(magnitude)):
        ewma[i] = alpha * magnitude[i] + (1 - alpha) * ewma[i-1]
    centered = magnitude - np.nanmedian(magnitude)
    k = np.nanmedian(np.abs(centered)) + 1e-6
    pos = np.zeros_like(centered)
    neg = np.zeros_like(centered)
    for i in range(1, len(centered)):
        pos[i] = max(0.0, pos[i-1] + centered[i] - 0.5 * k)
        neg[i] = min(0.0, neg[i-1] + centered[i] + 0.5 * k)
    cusum = np.maximum(pos, np.abs(neg))
    return _normalize(ewma), _normalize(cusum)


def _regions(frame: pd.DataFrame, scores: np.ndarray, flags: np.ndarray, contributions: np.ndarray, columns: list[str]) -> list[dict]:
    regions: list[dict] = []
    start = None
    for i, flag in enumerate(flags):
        if flag and start is None:
            start = i
        if start is not None and (not flag or i == len(flags) - 1):
            end = i if flag and i == len(flags) - 1 else i - 1
            c = contributions[start:end+1].mean(axis=0)
            order = np.argsort(c)[::-1][:5]
            regions.append({
                "start_index": int(start),
                "end_index": int(end),
                "start_time": frame.timestamp.iloc[start].isoformat(),
                "end_time": frame.timestamp.iloc[end].isoformat(),
                "score": float(np.max(scores[start:end+1])),
                "mean_score": float(np.mean(scores[start:end+1])),
                "top_signals": [columns[int(j)] for j in order if j < len(columns)],
                "duration_samples": int(end - start + 1),
            })
            start = None
    return sorted(regions, key=lambda r: r["score"], reverse=True)[:20]


def run_anomaly_detection(frame: pd.DataFrame, contamination: float = 0.08) -> dict:
    features = engineer_features(frame)
    matrix, columns = model_matrix(features)
    if len(matrix) < 12 or len(columns) < 2:
        return {"regions": [], "point_scores": [0.0] * len(frame), "feature_columns": columns, "model_name": "Sentinel Ensemble", "status": "insufficient_samples"}

    scaler = RobustScaler()
    scaled = scaler.fit_transform(matrix)

    iforest = IsolationForest(
        n_estimators=320,
        contamination=min(max(contamination, 0.01), 0.2),
        random_state=42,
        n_jobs=-1,
    )
    iforest.fit(scaled)
    if_score = _normalize(-iforest.score_samples(scaled))

    n_components = max(1, min(8, scaled.shape[1] - 1, scaled.shape[0] - 1))
    pca = PCA(n_components=n_components, random_state=42)
    reduced = pca.fit_transform(scaled)
    recon = pca.inverse_transform(reduced)
    recon_error = _normalize(np.mean((scaled - recon) ** 2, axis=1))

    robust_z = _robust_z(scaled)
    ewma, cusum = _ewma_cusum_signal(scaled)

    # Fixed ensemble weights: interpretable and deterministic for the prototype.
    ensemble = 0.38 * if_score + 0.24 * recon_error + 0.16 * robust_z + 0.10 * ewma + 0.12 * cusum
    ensemble = _normalize(ensemble)
    threshold = float(np.quantile(ensemble, 1 - contamination))
    flags = ensemble >= threshold

    med = np.nanmedian(scaled, axis=0)
    contributions = np.abs(scaled - med)
    regions = _regions(frame, ensemble, flags, contributions, columns)

    return {
        "regions": regions,
        "point_scores": [float(x) for x in ensemble],
        "component_scores": {
            "isolation_forest": [float(x) for x in if_score],
            "pca_reconstruction": [float(x) for x in recon_error],
            "robust_z": [float(x) for x in robust_z],
            "ewma": [float(x) for x in ewma],
            "cusum": [float(x) for x in cusum],
        },
        "feature_columns": columns,
        "model_name": "Sentinel Ensemble IF+PCA+RobustZ+EWMA+CUSUM",
        "model_version": "sentinel-ensemble-0.2",
        "contamination": contamination,
        "threshold": threshold,
        "pca_explained_variance": float(np.sum(pca.explained_variance_ratio_)),
        "status": "ok",
    }
