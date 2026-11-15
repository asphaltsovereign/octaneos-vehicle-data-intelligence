from __future__ import annotations

import numpy as np
import pandas as pd


def _finite(series: pd.Series) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).dropna()


def compute_metrics(frame: pd.DataFrame) -> dict:
    dt = frame.timestamp.diff().dt.total_seconds()
    duration = max(0.0, (frame.timestamp.iloc[-1] - frame.timestamp.iloc[0]).total_seconds()) if len(frame) > 1 else 0.0
    distance = 0.0
    for i in range(1, len(frame)):
        sec = dt.iloc[i]
        if pd.notna(sec) and 0 < sec <= 30 and pd.notna(frame.speed.iloc[i-1]) and pd.notna(frame.speed.iloc[i]):
            distance += ((frame.speed.iloc[i-1] + frame.speed.iloc[i]) / 2) * sec / 3600

    speed = _finite(frame.speed)
    rpm = _finite(frame.rpm)
    temp = _finite(frame.temp)
    battery = _finite(frame.battery)
    fuel = _finite(frame.fuel_rate)
    moving = frame[frame.speed.fillna(0) >= 5]
    stopped = frame[frame.speed.fillna(0) <= 3]

    return {
        "duration_sec": round(duration, 2),
        "distance_km": round(float(distance), 4),
        "avg_speed": round(float(speed.mean()), 3) if len(speed) else None,
        "max_speed": round(float(speed.max()), 3) if len(speed) else None,
        "avg_rpm": round(float(rpm.mean()), 3) if len(rpm) else None,
        "max_rpm": round(float(rpm.max()), 3) if len(rpm) else None,
        "avg_temp": round(float(temp.mean()), 3) if len(temp) else None,
        "max_temp": round(float(temp.max()), 3) if len(temp) else None,
        "min_battery": round(float(battery.min()), 3) if len(battery) else None,
        "median_battery": round(float(battery.median()), 3) if len(battery) else None,
        "moving_battery": round(float(_finite(moving.battery).median()), 3) if len(_finite(moving.battery)) else None,
        "avg_fuel_rate": round(float(fuel.mean()), 3) if len(fuel) else None,
        "moving_ratio": round(float(len(moving) / len(frame)), 4) if len(frame) else 0,
        "idle_ratio": round(float(len(stopped) / len(frame)), 4) if len(frame) else 0,
        "gps_coverage": round(float(frame.gps_fix.fillna(0).mean()), 4) if len(frame) else 0,
        "timing_gaps": int((dt > 15).sum()),
    }


def run_engineering_rules(frame: pd.DataFrame, source: str, metrics: dict) -> list[dict]:
    findings: list[dict] = []
    if metrics["timing_gaps"]:
        findings.append({"id": "DATA_GAP", "severity": "medium", "confidence": 0.95, "subsystem": "telemetry", "title": "Telemetry timing gaps detected", "signals": ["timestamp"]})
    if metrics["gps_coverage"] < 0.8:
        findings.append({"id": "GPS_COVERAGE", "severity": "low", "confidence": 0.8, "subsystem": "telemetry", "title": "Reduced GPS evidence coverage", "signals": ["gps_fix"]})

    if source == "ved":
        if metrics["idle_ratio"] > 0.35:
            findings.append({"id": "HIGH_IDLE", "severity": "low", "confidence": 0.65, "subsystem": "operation", "title": "High stop/idle ratio", "signals": ["speed", "rpm"]})
        if metrics["max_rpm"] is not None and metrics["max_rpm"] > 4500:
            findings.append({"id": "HIGH_RPM", "severity": "low", "confidence": 0.65, "subsystem": "operation", "title": "High RPM band observed", "signals": ["rpm"]})
        if metrics["avg_fuel_rate"] is not None and metrics["avg_fuel_rate"] > 6:
            findings.append({"id": "FUEL_RATE_HIGH", "severity": "low", "confidence": 0.45, "subsystem": "fuel", "title": "Elevated average fuel-rate period", "signals": ["fuel_rate", "speed", "rpm"]})
    else:
        mv = metrics.get("moving_battery")
        if mv is not None and mv < 13.2:
            findings.append({"id": "MOVING_UNDERVOLTAGE", "severity": "medium", "confidence": 0.65, "subsystem": "electrical", "title": "Possible under-voltage during movement", "signals": ["battery", "speed"]})
        if mv is not None and mv > 14.9:
            findings.append({"id": "MOVING_OVERVOLTAGE", "severity": "high", "confidence": 0.72, "subsystem": "electrical", "title": "Possible charging over-voltage", "signals": ["battery", "speed"]})
    return findings
