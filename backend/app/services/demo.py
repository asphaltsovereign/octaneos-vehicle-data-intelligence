from __future__ import annotations

import numpy as np
import pandas as pd


def _urban_speed_profile(samples: int = 120) -> np.ndarray:
    """Deterministic multi-phase synthetic urban drive profile.

    This is presentation/validation telemetry, not measured vehicle data.  The profile
    deliberately includes acceleration, cruise, deceleration, and a second cruise phase
    so the demo looks like an operating cycle rather than a single triangular ramp.
    """
    anchors_x = np.array([0, 8, 22, 34, 43, 54, 67, 76, 88, 101, 111, 119], dtype=float)
    anchors_v = np.array([0, 18, 43, 44, 27, 51, 51, 36, 57, 56, 24, 0], dtype=float)
    x = np.arange(samples, dtype=float)
    speed = np.interp(x, anchors_x, anchors_v)

    # Keep cruise sections visually stable while retaining small deterministic road-load variation.
    ripple = 0.45 * np.sin(x / 4.7) + 0.20 * np.sin(x / 2.3)
    cruise_mask = ((x >= 22) & (x <= 34)) | ((x >= 54) & (x <= 67)) | ((x >= 88) & (x <= 101))
    speed = speed + np.where(cruise_mask, ripple * 0.22, ripple)
    return np.clip(speed, 0.0, None)


def demo_frame() -> pd.DataFrame:
    rows = []
    base = pd.Timestamp("2026-09-07T12:00:00Z")
    speed_profile = _urban_speed_profile(120)
    acceleration = np.diff(speed_profile, prepend=speed_profile[0])

    for i, speed in enumerate(speed_profile):
        phase = i / 119
        accel = acceleration[i]
        throttle_load = max(accel, 0.0)
        rpm = 880 + speed * 42 + throttle_load * 95 + 45 * np.sin(i / 3.8)
        engine_load = np.clip(20 + speed * 0.52 + throttle_load * 5.5 + 2.2 * np.sin(i / 5.2), 12, 92)
        maf = 3.4 + rpm * 0.0042 + engine_load * 0.075
        fuel_rate = 0.72 + speed * 0.038 + engine_load * 0.012

        rows.append({
            "timestamp": base + pd.Timedelta(seconds=i * 2),
            "speed": float(speed),
            "rpm": float(max(820, rpm)),
            "maf": float(maf),
            "engine_load": float(engine_load),
            "temp": float(28.0 + phase * 4.5 + 0.25 * np.sin(i / 11)),
            "fuel_rate": float(fuel_rate),
            "battery": float(13.74 + 0.018 * np.sin(i / 4.4)),
            "soc": float(70 - phase * 2),
            "lat": 13.0827 + i * 0.00002,
            "lon": 80.2707 + i * 0.00002,
            "gps_fix": 1,
        })
    return pd.DataFrame(rows)
