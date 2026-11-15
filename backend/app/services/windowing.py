from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

CORE_SIGNALS = ["speed", "rpm", "maf", "engine_load"]
OPTIONAL_SIGNALS = ["temp", "fuel_rate", "battery", "soc"]
RAW_SIGNALS = CORE_SIGNALS + OPTIONAL_SIGNALS


@dataclass(frozen=True)
class WindowRecord:
    session_id: str
    start_index: int
    end_index: int
    start_time: str
    end_time: str


def _slope(values: pd.Series) -> float:
    y = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(y)
    if valid.sum() < 3:
        return np.nan
    x = np.arange(len(y), dtype=float)[valid]
    y = y[valid]
    x = x - x.mean()
    denom = np.sum(x * x)
    return float(np.sum(x * (y - y.mean())) / denom) if denom > 0 else 0.0


def _corr(a: pd.Series, b: pd.Series) -> float:
    x = pd.to_numeric(a, errors="coerce")
    y = pd.to_numeric(b, errors="coerce")
    mask = x.notna() & y.notna()
    if mask.sum() < 4:
        return np.nan
    xv = x[mask].to_numpy(float)
    yv = y[mask].to_numpy(float)
    if np.nanstd(xv) < 1e-12 or np.nanstd(yv) < 1e-12:
        return 0.0
    return float(np.corrcoef(xv, yv)[0, 1])


def _window_features(chunk: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {}
    for signal in RAW_SIGNALS:
        s = pd.to_numeric(chunk.get(signal, pd.Series(index=chunk.index, dtype=float)), errors="coerce")
        finite = s[np.isfinite(s)]
        coverage = float(finite.size / max(len(chunk), 1))
        out[f"{signal}__coverage"] = coverage
        if finite.empty:
            for suffix in ["mean", "std", "min", "max", "range", "slope", "delta"]:
                out[f"{signal}__{suffix}"] = np.nan
            continue
        out[f"{signal}__mean"] = float(finite.mean())
        out[f"{signal}__std"] = float(finite.std(ddof=0))
        out[f"{signal}__min"] = float(finite.min())
        out[f"{signal}__max"] = float(finite.max())
        out[f"{signal}__range"] = float(finite.max() - finite.min())
        out[f"{signal}__slope"] = _slope(s)
        out[f"{signal}__delta"] = float(finite.iloc[-1] - finite.iloc[0]) if len(finite) >= 2 else 0.0

    speed = pd.to_numeric(chunk.get("speed"), errors="coerce")
    rpm = pd.to_numeric(chunk.get("rpm"), errors="coerce")
    maf = pd.to_numeric(chunk.get("maf"), errors="coerce")
    engine_load = pd.to_numeric(chunk.get("engine_load"), errors="coerce")
    fuel = pd.to_numeric(chunk.get("fuel_rate"), errors="coerce")
    battery = pd.to_numeric(chunk.get("battery"), errors="coerce")
    temp = pd.to_numeric(chunk.get("temp"), errors="coerce")

    out["corr__rpm_speed"] = _corr(rpm, speed)
    out["corr__rpm_maf"] = _corr(rpm, maf)
    out["corr__rpm_load"] = _corr(rpm, engine_load)
    out["corr__maf_load"] = _corr(maf, engine_load)
    out["corr__speed_load"] = _corr(speed, engine_load)
    out["corr__speed_maf"] = _corr(speed, maf)
    out["corr__rpm_fuel"] = _corr(rpm, fuel)
    out["corr__rpm_battery"] = _corr(rpm, battery)
    out["corr__speed_fuel"] = _corr(speed, fuel)
    out["corr__rpm_temp"] = _corr(rpm, temp)

    if "timestamp" in chunk:
        ts = pd.to_datetime(chunk["timestamp"], utc=True, errors="coerce")
        dt = ts.diff().dt.total_seconds()
        finite_dt = dt[np.isfinite(dt)]
        out["timing__dt_mean"] = float(finite_dt.mean()) if len(finite_dt) else np.nan
        out["timing__dt_std"] = float(finite_dt.std(ddof=0)) if len(finite_dt) else np.nan
        out["timing__gap_ratio"] = float((finite_dt > 15).mean()) if len(finite_dt) else 0.0
    else:
        out["timing__dt_mean"] = np.nan
        out["timing__dt_std"] = np.nan
        out["timing__gap_ratio"] = np.nan

    if len(speed) >= 3 and "timestamp" in chunk:
        ts = pd.to_datetime(chunk["timestamp"], utc=True, errors="coerce")
        dt = ts.diff().dt.total_seconds().replace(0, np.nan)
        acceleration = (speed.diff() / 3.6) / dt
        valid_acc = acceleration[np.isfinite(acceleration)]
        out["dynamics__accel_mean"] = float(valid_acc.mean()) if len(valid_acc) else np.nan
        out["dynamics__accel_std"] = float(valid_acc.std(ddof=0)) if len(valid_acc) else np.nan
        out["dynamics__accel_abs_max"] = float(valid_acc.abs().max()) if len(valid_acc) else np.nan
    else:
        out["dynamics__accel_mean"] = np.nan
        out["dynamics__accel_std"] = np.nan
        out["dynamics__accel_abs_max"] = np.nan

    gps = pd.to_numeric(chunk.get("gps_fix", pd.Series(1, index=chunk.index)), errors="coerce")
    out["quality__gps_fix_ratio"] = float(gps.fillna(0).mean())
    core_present = [c for c in CORE_SIGNALS if c in chunk.columns]
    out["quality__core_missing_ratio"] = float(chunk[core_present].isna().mean().mean()) if core_present else 1.0
    out["quality__available_signal_count"] = float(sum(chunk[c].notna().any() for c in RAW_SIGNALS if c in chunk.columns))
    return out


def build_window_matrix(
    frame: pd.DataFrame,
    session_id: str,
    window_size: int = 16,
    stride: int = 8,
    min_coverage: float = 0.25,
) -> tuple[pd.DataFrame, list[WindowRecord]]:
    if window_size < 4 or stride < 1:
        raise ValueError("window_size must be >=4 and stride must be >=1")
    if len(frame) < window_size:
        return pd.DataFrame(), []

    rows: list[dict[str, float]] = []
    meta: list[WindowRecord] = []
    for start in range(0, len(frame) - window_size + 1, stride):
        end = start + window_size
        chunk = frame.iloc[start:end]
        feats = _window_features(chunk)
        signal_coverages = [feats.get(f"{s}__coverage", 0.0) for s in RAW_SIGNALS]
        if max(signal_coverages, default=0.0) < min_coverage:
            continue
        rows.append(feats)
        meta.append(WindowRecord(
            session_id=session_id,
            start_index=start,
            end_index=end - 1,
            start_time=pd.Timestamp(chunk.timestamp.iloc[0]).isoformat(),
            end_time=pd.Timestamp(chunk.timestamp.iloc[-1]).isoformat(),
        ))
    return pd.DataFrame(rows), meta


def combine_window_matrices(
    sessions: Iterable[tuple[str, pd.DataFrame]],
    window_size: int = 16,
    stride: int = 8,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    matrices: list[pd.DataFrame] = []
    metadata: list[dict] = []
    for session_id, frame in sessions:
        matrix, meta = build_window_matrix(frame, session_id, window_size=window_size, stride=stride)
        if matrix.empty:
            continue
        matrices.append(matrix)
        metadata.extend([m.__dict__ for m in meta])
    if not matrices:
        return pd.DataFrame(), pd.DataFrame()
    feature_df = pd.concat(matrices, ignore_index=True, sort=False)
    meta_df = pd.DataFrame(metadata)
    return feature_df, meta_df
