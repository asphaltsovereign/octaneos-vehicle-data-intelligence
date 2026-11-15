from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .anomaly import run_anomaly_detection
from .demo import demo_frame
from .simulator import inject_fault

SCENARIOS = ["rpm_instability", "maf_drift", "load_instability", "sensor_dropout", "signal_spikes", "thermal_drift", "voltage_degradation"]


def _range_mask(n: int, scenario: str) -> np.ndarray:
    # Mirrors simulator's central disturbance window for validation scoring.
    mask = np.zeros(n, dtype=bool)
    start, end = int(n * 0.35), int(n * 0.65)
    if scenario in {"sensor_dropout", "signal_spikes"}:
        start, end = int(n * 0.42), int(n * 0.58)
    mask[start:end] = True
    return mask


def run_validation_campaign(repeats: int = 4) -> dict:
    total_fault = detected_fault = total_normal = false_positive = 0
    latencies: list[int] = []
    scenario_results = []

    for scenario in SCENARIOS:
        s_detected = s_total = 0
        for _ in range(repeats):
            frame = inject_fault(demo_frame(), scenario)
            result = run_anomaly_detection(frame)
            scores = np.array(result["point_scores"], dtype=float)
            if not len(scores):
                continue
            threshold = float(result.get("threshold", 0.8))
            pred = scores >= threshold
            truth = _range_mask(len(frame), scenario)
            total_fault += int(truth.sum())
            detected_fault += int((pred & truth).sum())
            total_normal += int((~truth).sum())
            false_positive += int((pred & ~truth).sum())
            s_total += int(truth.sum())
            s_detected += int((pred & truth).sum())
            truth_idx = np.where(truth)[0]
            hit_idx = np.where(pred & truth)[0]
            if len(truth_idx) and len(hit_idx):
                latencies.append(max(0, int(hit_idx[0] - truth_idx[0])))
        scenario_results.append({
            "scenario": scenario,
            "detection_rate": round(s_detected / max(s_total, 1), 4),
        })

    detection_rate = detected_fault / max(total_fault, 1)
    fpr = false_positive / max(total_normal, 1)
    return {
        "campaign": "synthetic-fault-validation-v0.1",
        "repeats_per_scenario": repeats,
        "scenarios": len(SCENARIOS) * repeats,
        "detection_rate": round(detection_rate, 4),
        "false_positive_rate": round(fpr, 4),
        "median_detection_latency_samples": float(np.median(latencies)) if latencies else None,
        "scenario_results": scenario_results,
        "claim_boundary": "Synthetic fault injection validates detection behavior only; it is not real component-failure accuracy.",
    }
