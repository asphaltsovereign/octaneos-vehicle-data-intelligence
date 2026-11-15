from __future__ import annotations

import numpy as np
import pandas as pd

SCENARIOS = [
    "normal",
    "rpm_instability",
    "maf_drift",
    "load_instability",
    "sensor_dropout",
    "signal_spikes",
    "thermal_drift",
    "voltage_degradation",
]
SEVERITIES = ["mild", "medium", "severe"]


def fault_bounds(n: int) -> tuple[int, int]:
    """Return inclusive sample bounds for the controlled perturbation."""
    start = max(2, n // 3)
    end_exclusive = min(n, start + max(5, n // 4))
    return start, end_exclusive - 1


def inject_fault(frame: pd.DataFrame, scenario: str, seed: int = 42, severity: str = "medium") -> pd.DataFrame:
    """Inject a controlled perturbation for sensitivity testing.

    The scenario and severity are never passed to the anomaly model as labels. They are
    retained only by the validation harness as experiment ground truth.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario. Choose one of: {', '.join(SCENARIOS)}")
    if severity not in SEVERITIES:
        raise ValueError(f"Unknown severity. Choose one of: {', '.join(SEVERITIES)}")

    out = frame.copy()
    if scenario == "normal" or len(out) < 8:
        return out

    rng = np.random.default_rng(seed)
    start, end = fault_bounds(len(out))
    idx = out.index[start : end + 1]
    if len(idx) == 0:
        return out

    severity_index = SEVERITIES.index(severity)

    if scenario == "voltage_degradation":
        if "battery" not in out or out.battery.notna().sum() < 5:
            raise ValueError("Voltage degradation requires a dataset/model capability with battery coverage.")
        max_drop = [0.45, 1.20, 2.20][severity_index]
        out.loc[idx, "battery"] = out.loc[idx, "battery"] - np.linspace(0.05, max_drop, len(idx))

    elif scenario == "rpm_instability":
        if "rpm" not in out or out.rpm.notna().sum() < 5:
            raise ValueError("RPM instability requires a dataset with RPM coverage.")
        sigma = [0.08, 0.20, 0.38][severity_index]
        out.loc[idx, "rpm"] = np.maximum(0, out.loc[idx, "rpm"] * (1 + rng.normal(0, sigma, len(idx))))

    elif scenario == "maf_drift":
        if "maf" not in out or out.maf.notna().sum() < 5:
            raise ValueError("MAF drift requires a dataset with MAF coverage.")
        end_factor = [1.18, 1.55, 2.20][severity_index]
        out.loc[idx, "maf"] = np.maximum(0, out.loc[idx, "maf"] * np.linspace(1.02, end_factor, len(idx)))

    elif scenario == "load_instability":
        if "engine_load" not in out or out.engine_load.notna().sum() < 5:
            raise ValueError("Load instability requires a dataset with engine-load coverage.")
        sigma = [0.10, 0.28, 0.55][severity_index]
        out.loc[idx, "engine_load"] = np.clip(
            out.loc[idx, "engine_load"] * (1 + rng.normal(0, sigma, len(idx))), 0, 100
        )

    elif scenario == "thermal_drift":
        if "temp" not in out or out.temp.notna().sum() < 5:
            raise ValueError("Thermal drift requires a dataset/model capability with temperature coverage.")
        max_rise = [4.0, 10.0, 20.0][severity_index]
        out.loc[idx, "temp"] = out.loc[idx, "temp"] + np.linspace(0, max_rise, len(idx))

    elif scenario == "sensor_dropout":
        # Contiguous / partial missingness is intentionally applied to signals that the
        # session actually provides. It tests the Signal Guardian + ML feature path.
        fraction = [0.34, 0.67, 1.0][severity_index]
        candidates = [c for c in ["speed", "rpm", "maf", "engine_load"] if c in out and out[c].notna().sum() >= 5]
        if not candidates:
            raise ValueError("Sensor dropout requires at least one core telemetry signal.")
        step = max(1, int(round(1 / max(fraction, 1e-6))))
        drop_idx = idx[::step] if severity != "severe" else idx
        # Mild drops one channel; medium drops up to two; severe drops all available core channels.
        channel_count = [1, min(2, len(candidates)), len(candidates)][severity_index]
        for c in candidates[:channel_count]:
            out.loc[drop_idx, c] = np.nan
        if "gps_fix" in out:
            out.loc[drop_idx, "gps_fix"] = 0

    elif scenario == "signal_spikes":
        spike_count = [2, 4, 6][severity_index]
        positions = np.linspace(0, len(idx) - 1, num=min(spike_count, len(idx)), dtype=int)
        spike_idx = idx[positions]
        speed_add = [(12, 25), (35, 70), (70, 120)][severity_index]
        rpm_add = [(350, 900), (1500, 3000), (3000, 5500)][severity_index]
        out.loc[spike_idx, "speed"] = out.loc[spike_idx, "speed"].fillna(0) + rng.uniform(*speed_add, len(spike_idx))
        if "rpm" in out and out.rpm.notna().any():
            out.loc[spike_idx, "rpm"] = out.loc[spike_idx, "rpm"].fillna(1200) + rng.uniform(*rpm_add, len(spike_idx))

    return out
