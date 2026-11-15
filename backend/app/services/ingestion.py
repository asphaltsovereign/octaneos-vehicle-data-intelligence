from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
from typing import Literal

import numpy as np
import pandas as pd


SAN_REQUIRED = [
    "schema_version", "device_id", "vehicle_id", "session_id", "sample_seq",
    "timestamp_utc", "battery_v", "ambient_temp_c", "gps_lat", "gps_lon",
    "gps_speed_kmh", "gps_fix",
]

VED_ALIASES = {
    "vehicle_id": ["VehId", "VehicleId", "vehicle_id"],
    "trip": ["Trip", "TripId", "trip_id"],
    "timestamp_ms": ["Timestamp(ms)", "Timestamp", "Time(ms)", "time_ms"],
    "day_num": ["DayNum", "Day", "day_num"],
    "lat": ["Latitude[deg]", "Latitude", "gps_lat", "lat"],
    "lon": ["Longitude[deg]", "Longitude", "gps_lon", "lon"],
    "speed": ["Vehicle Speed[km/h]", "Vehicle Speed", "Speed[km/h]", "speed_kmh"],
    "rpm": ["Engine RPM[RPM]", "Engine RPM", "RPM", "engine_rpm"],
    "maf": ["MAF[g/sec]", "MAF", "Mass Air Flow[g/sec]", "maf_gps", "maf"],
    "engine_load": ["Absolute Load[%]", "Absolute Load", "Engine Load[%]", "engine_load_pct", "engine_load"],
    "temp": ["OAT[DegC]", "Outside Air Temperature[DegC]", "Outside Air Temperature", "Ambient Temperature", "ambient_temp_c"],
    "fuel_rate": ["Fuel Rate[L/hr]", "Fuel Rate", "fuel_rate_lhr"],
    "battery": ["HV Battery Voltage[V]", "Battery Voltage[V]", "Battery Voltage", "battery_v"],
    "soc": ["HV Battery SOC[%]", "Battery SOC[%]", "SOC", "soc"],
}


@dataclass
class IngestedSession:
    source_type: Literal["ved", "san"]
    session_id: str
    vehicle_id: str
    device_id: str
    file_hash: str
    frame: pd.DataFrame
    quality_score: int
    analysis_ready: bool
    quality_notes: list[str]


def _first_existing(df: pd.DataFrame, aliases: list[str]) -> str | None:
    normalized = {c.lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    for alias in aliases:
        key = alias.lower().replace(" ", "").replace("_", "")
        if key in normalized:
            return normalized[key]
    return None


def detect_source(df: pd.DataFrame) -> Literal["ved", "san"]:
    cols = set(df.columns)
    if set(SAN_REQUIRED).issubset(cols):
        return "san"
    has_speed = _first_existing(df, VED_ALIASES["speed"])
    has_trip = _first_existing(df, VED_ALIASES["trip"])
    has_vehicle = _first_existing(df, VED_ALIASES["vehicle_id"])
    has_time = _first_existing(df, VED_ALIASES["timestamp_ms"])
    if has_speed and has_trip and has_vehicle and has_time:
        return "ved"
    raise ValueError("Unsupported CSV contract. Expected SAN-V1 native headers or VED-style vehicle/trip/time/speed fields.")


def _numeric(df: pd.DataFrame, aliases: list[str]) -> pd.Series:
    col = _first_existing(df, aliases)
    if not col:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def _normalize_ved(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    vehicle_col = _first_existing(df, VED_ALIASES["vehicle_id"])
    trip_col = _first_existing(df, VED_ALIASES["trip"])
    time_col = _first_existing(df, VED_ALIASES["timestamp_ms"])
    day_col = _first_existing(df, VED_ALIASES["day_num"])
    if not all([vehicle_col, trip_col, time_col]):
        raise ValueError("VED import requires vehicle id, trip id and timestamp.")

    if df[vehicle_col].nunique(dropna=True) > 1 or df[trip_col].nunique(dropna=True) > 1:
        raise ValueError("Import one VED vehicle-trip per CSV.")

    t_ms = pd.to_numeric(df[time_col], errors="coerce")
    if t_ms.isna().any():
        raise ValueError("VED timestamp contains invalid values.")
    day = pd.to_numeric(df[day_col], errors="coerce") if day_col else pd.Series(1, index=df.index)
    base = pd.Timestamp("2017-11-01", tz="UTC")
    timestamp = base + pd.to_timedelta((day.fillna(1) - 1), unit="D") + pd.to_timedelta(t_ms, unit="ms")

    out = pd.DataFrame({
        "timestamp": timestamp,
        "speed": _numeric(df, VED_ALIASES["speed"]),
        "rpm": _numeric(df, VED_ALIASES["rpm"]),
        "maf": _numeric(df, VED_ALIASES["maf"]),
        "engine_load": _numeric(df, VED_ALIASES["engine_load"]),
        "temp": _numeric(df, VED_ALIASES["temp"]),
        "fuel_rate": _numeric(df, VED_ALIASES["fuel_rate"]),
        "battery": _numeric(df, VED_ALIASES["battery"]),
        "soc": _numeric(df, VED_ALIASES["soc"]),
        "lat": _numeric(df, VED_ALIASES["lat"]),
        "lon": _numeric(df, VED_ALIASES["lon"]),
    })
    out["gps_fix"] = ((out.lat.notna()) & (out.lon.notna()) & ~((out.lat == 0) & (out.lon == 0))).astype(int)
    identity = {
        "session_id": f"VED-{df[vehicle_col].iloc[0]}-TRIP-{df[trip_col].iloc[0]}",
        "vehicle_id": f"VED-{df[vehicle_col].iloc[0]}",
        "device_id": "PUBLIC-VED",
    }
    return out, identity


def _normalize_san(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    for field in ["device_id", "vehicle_id", "session_id"]:
        if df[field].nunique(dropna=True) != 1:
            raise ValueError(f"SAN-V1 {field} must be constant within one file.")
    out = pd.DataFrame({
        "timestamp": pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce"),
        "speed": pd.to_numeric(df["gps_speed_kmh"], errors="coerce"),
        "rpm": np.nan,
        "maf": np.nan,
        "engine_load": np.nan,
        "temp": pd.to_numeric(df["ambient_temp_c"], errors="coerce"),
        "fuel_rate": np.nan,
        "battery": pd.to_numeric(df["battery_v"], errors="coerce"),
        "soc": np.nan,
        "lat": pd.to_numeric(df["gps_lat"], errors="coerce"),
        "lon": pd.to_numeric(df["gps_lon"], errors="coerce"),
        "gps_fix": pd.to_numeric(df["gps_fix"], errors="coerce"),
    })
    identity = {
        "session_id": str(df["session_id"].iloc[0]),
        "vehicle_id": str(df["vehicle_id"].iloc[0]),
        "device_id": str(df["device_id"].iloc[0]),
    }
    return out, identity


def _quality(frame: pd.DataFrame, source: str) -> tuple[int, bool, list[str]]:
    notes: list[str] = []
    n = len(frame)
    if n < 10:
        notes.append("Fewer than 10 samples.")
    if frame.timestamp.isna().any() or not frame.timestamp.is_monotonic_increasing:
        notes.append("Timestamp integrity failed.")
    gps = float(frame.gps_fix.fillna(0).mean()) if n else 0.0
    moving = int((frame.speed.fillna(0) >= 5).sum())
    speed_max = float(frame.speed.max()) if frame.speed.notna().any() else 0.0
    speed_range = float(frame.speed.max() - frame.speed.min()) if frame.speed.notna().any() else 0.0
    rpm_cov = float(frame.rpm.notna().mean())
    active_rpm = int((frame.rpm.fillna(0) >= 600).sum())

    dt = frame.timestamp.diff().dt.total_seconds()
    gaps = int((dt > 15).sum())
    continuity = max(0.0, 1.0 - min(gaps * 0.05, 0.6))

    if source == "ved":
        score = round(
            10 + 15 * continuity + 10 * gps + 10 * rpm_cov
            + 20 * (moving >= 10) + 15 * (active_rpm >= 10)
            + 10 * (speed_range >= 5) + 10 * (n >= 10)
        )
        ready = n >= 10 and moving >= 5 and speed_max >= 10 and speed_range >= 5 and (rpm_cov < 0.2 or active_rpm >= 10)
    else:
        score = round(40 + 20 * continuity + 20 * gps + 20 * (n >= 4))
        ready = n >= 4 and not frame.timestamp.isna().any()

    if gps < 0.8:
        notes.append(f"GPS coverage is {gps:.0%}.")
    if gaps:
        notes.append(f"{gaps} timing gaps exceed 15 seconds.")
    if not ready:
        notes.append("Session rejected by analysis-readiness gate.")
    return int(max(0, min(100, score))), bool(ready), notes


def ingest_csv_bytes(raw: bytes) -> IngestedSession:
    digest = hashlib.sha256(raw).hexdigest()
    df = pd.read_csv(io.BytesIO(raw))
    if len(df) < 2:
        raise ValueError("CSV needs at least two telemetry samples.")
    source = detect_source(df)
    frame, identity = _normalize_san(df) if source == "san" else _normalize_ved(df)

    if frame.timestamp.isna().any():
        raise ValueError("Invalid timestamp values detected.")
    if not frame.timestamp.is_monotonic_increasing:
        raise ValueError("Timestamps must increase sequentially.")
    if ((frame.speed.dropna() < 0) | (frame.speed.dropna() > 280)).any():
        raise ValueError("Speed outside accepted 0-280 km/h range.")
    if ((frame.rpm.dropna() < 0) | (frame.rpm.dropna() > 12000)).any():
        raise ValueError("RPM outside accepted 0-12000 range.")

    score, ready, notes = _quality(frame, source)
    return IngestedSession(source, **identity, file_hash=digest, frame=frame, quality_score=score, analysis_ready=ready, quality_notes=notes)
