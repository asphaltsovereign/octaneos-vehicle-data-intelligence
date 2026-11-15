from __future__ import annotations

import numpy as np
import pandas as pd

SIGNALS = ["speed", "rpm", "maf", "engine_load", "temp", "fuel_rate", "battery", "soc"]


def _safe_corr(a: pd.Series, b: pd.Series, window: int) -> pd.Series:
    return a.rolling(window, min_periods=max(3, window // 2)).corr(b)


def engineer_features(frame: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    x = frame.copy()
    t = x.timestamp.astype("int64") / 1e9
    dt = pd.Series(t, index=x.index).diff().replace(0, np.nan)

    speed_ms = x.speed / 3.6
    x["acceleration"] = speed_ms.diff() / dt
    x["jerk"] = x["acceleration"].diff() / dt
    x["speed_delta"] = x.speed.diff()
    x["rpm_delta"] = x.rpm.diff()
    x["maf_gradient"] = x.maf.diff() / dt if "maf" in x else np.nan
    x["engine_load_gradient"] = x.engine_load.diff() / dt if "engine_load" in x else np.nan
    x["temp_gradient"] = x.temp.diff() / dt
    x["voltage_gradient"] = x.battery.diff() / dt
    x["fuel_rate_change"] = x.fuel_rate.diff() / dt
    x["rpm_speed_ratio"] = x.rpm / x.speed.replace(0, np.nan)
    x["fuel_per_rpm"] = x.fuel_rate / x.rpm.replace(0, np.nan)
    x["fuel_per_speed"] = x.fuel_rate / x.speed.replace(0, np.nan)

    for signal in SIGNALS:
        if signal in x:
            x[f"{signal}_roll_mean"] = x[signal].rolling(window, min_periods=2).mean()
            x[f"{signal}_roll_std"] = x[signal].rolling(window, min_periods=2).std()
            x[f"{signal}_roll_min"] = x[signal].rolling(window, min_periods=2).min()
            x[f"{signal}_roll_max"] = x[signal].rolling(window, min_periods=2).max()
            x[f"{signal}_roll_range"] = x[f"{signal}_roll_max"] - x[f"{signal}_roll_min"]

    x["rpm_speed_corr"] = _safe_corr(x.rpm, x.speed, window)
    if "maf" in x:
        x["rpm_maf_corr"] = _safe_corr(x.rpm, x.maf, window)
        x["speed_maf_corr"] = _safe_corr(x.speed, x.maf, window)
    if "engine_load" in x:
        x["rpm_load_corr"] = _safe_corr(x.rpm, x.engine_load, window)
        x["speed_load_corr"] = _safe_corr(x.speed, x.engine_load, window)
    if "maf" in x and "engine_load" in x:
        x["maf_load_corr"] = _safe_corr(x.maf, x.engine_load, window)
    x["rpm_fuel_corr"] = _safe_corr(x.rpm, x.fuel_rate, window)
    x["rpm_voltage_corr"] = _safe_corr(x.rpm, x.battery, window)
    x["speed_fuel_corr"] = _safe_corr(x.speed, x.fuel_rate, window)
    x["temp_load_corr"] = _safe_corr(x.temp, x.rpm, window)

    # Data quality / signal integrity proxies.
    x["sampling_interval_s"] = dt
    median_dt = float(np.nanmedian(dt.to_numpy())) if dt.notna().any() else np.nan
    x["sampling_jitter"] = (dt - median_dt).abs() if np.isfinite(median_dt) else np.nan
    x["gps_dropout"] = (x.get("gps_fix", 1) == 0).astype(float) if "gps_fix" in x else 0.0
    x["rpm_stuck_score"] = (x.rpm.diff().abs().rolling(window, min_periods=2).mean() < 1e-6).astype(float)
    x["speed_stuck_score"] = (x.speed.diff().abs().rolling(window, min_periods=2).mean() < 1e-6).astype(float)
    return x


def model_matrix(features: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    excluded = {"timestamp", "gps_lat", "gps_lon"}
    candidates = [
        c for c in features.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(features[c])
    ]
    usable = [
        c for c in candidates
        if features[c].notna().sum() >= max(5, len(features) // 10)
        and features[c].nunique(dropna=True) > 1
    ]
    if not usable:
        usable = [c for c in ["speed", "temp", "battery"] if c in features and features[c].notna().any()]
    matrix = features[usable].replace([np.inf, -np.inf], np.nan)
    matrix = matrix.fillna(matrix.median(numeric_only=True)).fillna(0.0)
    return matrix, usable
