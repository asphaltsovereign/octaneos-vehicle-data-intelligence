"""Prepare quality-approved VED trips for Sentinel baseline training.

Usage:
    python scripts/prepare_ved.py --input-dir C:\\data\\VED --output-dir data\\prepared_ved --max-trips 80

The script streams weekly VED CSV files, selects one VehId+Trip at a time, applies
minimum activity/coverage gates, and writes compact per-trip CSVs. It does not alter
or redistribute the original dataset.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.ingestion import ingest_csv_bytes  # noqa: E402


def _find_col(group: pd.DataFrame, normalized_names: set[str]) -> str | None:
    return next((c for c in group.columns if re.sub(r"[^a-z0-9]", "", c.lower()) in normalized_names), None)


def _coverage(group: pd.DataFrame, column: str | None) -> float:
    if not column:
        return 0.0
    return float(pd.to_numeric(group[column], errors="coerce").notna().mean())


def is_candidate(group: pd.DataFrame) -> bool:
    """Powertrain-baseline gate: dynamic trip + strong RPM + MAF or engine-load context."""
    if len(group) < 80:
        return False
    speed_col = _find_col(group, {"vehiclespeedkmh", "vehiclespeed", "speedkmh"})
    rpm_col = _find_col(group, {"enginerpmrpm", "enginerpm", "rpm"})
    maf_col = _find_col(group, {"mafgsec", "maf", "massairflowgsec"})
    load_col = _find_col(group, {"absoluteload", "engineload"})
    if not speed_col or not rpm_col:
        return False

    speed = pd.to_numeric(group[speed_col], errors="coerce")
    rpm = pd.to_numeric(group[rpm_col], errors="coerce")
    if speed.notna().mean() < 0.95 or speed.max(skipna=True) < 20 or (speed >= 5).sum() < 30:
        return False
    if rpm.notna().mean() < 0.80 or (rpm >= 600).sum() < 30:
        return False

    maf_cov = _coverage(group, maf_col)
    load_cov = _coverage(group, load_col)
    if max(maf_cov, load_cov) < 0.50:
        return False
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", default="data/prepared_ved")
    ap.add_argument("--max-trips", type=int, default=80)
    ap.add_argument("--max-trips-per-vehicle", type=int, default=3)
    args = ap.parse_args()

    source = Path(args.input_dir)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    accepted = 0
    rows = []
    per_vehicle: dict[str, int] = {}

    for csv_path in sorted(source.rglob("VED_*_week.csv")):
        df = pd.read_csv(csv_path, low_memory=False)
        if "VehId" not in df or "Trip" not in df:
            continue
        for (veh, trip), group in df.groupby(["VehId", "Trip"], sort=False):
            if accepted >= args.max_trips:
                break
            veh_key = str(veh)
            if per_vehicle.get(veh_key, 0) >= args.max_trips_per_vehicle:
                continue
            group = group.copy().dropna(how="all")
            if not is_candidate(group):
                continue
            raw = group.to_csv(index=False).encode("utf-8")
            try:
                session = ingest_csv_bytes(raw)
            except Exception:
                continue
            if not session.analysis_ready or session.quality_score < 75:
                continue
            name = f"VED-{veh}-TRIP-{trip}.csv"
            (output / name).write_bytes(raw)
            accepted += 1
            per_vehicle[veh_key] = per_vehicle.get(veh_key, 0) + 1
            f = session.frame
            rows.append({
                "file": name,
                "vehicle_id": str(veh),
                "trip": str(trip),
                "samples": len(group),
                "quality_score": session.quality_score,
                "speed_max": float(session.frame.speed.max()),
                "rpm_coverage": float(f.rpm.notna().mean()),
                "maf_coverage": float(f.maf.notna().mean()),
                "engine_load_coverage": float(f.engine_load.notna().mean()),
                "oat_coverage": float(f.temp.notna().mean()),
                "fuel_rate_coverage": float(f.fuel_rate.notna().mean()),
                "battery_coverage": float(f.battery.notna().mean()),
                "soc_coverage": float(f.soc.notna().mean()),
                "model_compatibility_score": round(100 * (0.30*float(f.speed.notna().mean()) + 0.30*float(f.rpm.notna().mean()) + 0.20*float(f.maf.notna().mean()) + 0.20*float(f.engine_load.notna().mean())), 1),
                "sha256": session.file_hash,
            })
        if accepted >= args.max_trips:
            break

    index = pd.DataFrame(rows)
    index.to_csv(output / "prepared_index.csv", index=False)
    print(f"Prepared {accepted} quality-approved trips in {output}")
    if accepted:
        print(index[["vehicle_id", "trip", "samples", "quality_score", "speed_max"]].head(12).to_string(index=False))


if __name__ == "__main__":
    main()
