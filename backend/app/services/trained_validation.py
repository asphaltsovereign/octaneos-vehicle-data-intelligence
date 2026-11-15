from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import numpy as np

from .simulator import SEVERITIES, fault_bounds, inject_fault
from .training import DETECTOR_NAMES, TrainingSession, score_with_trained_model

VALIDATION_SCENARIOS = [
    "rpm_instability",
    "maf_drift",
    "load_instability",
    "sensor_dropout",
    "signal_spikes",
    "thermal_drift",
    "voltage_degradation",
]

SCENARIO_SIGNAL_REQUIREMENTS = {
    "rpm_instability": {"rpm"},
    "maf_drift": {"maf"},
    "load_instability": {"engine_load"},
    "sensor_dropout": {"speed"},
    "signal_spikes": {"speed"},
    "thermal_drift": {"temp"},
    "voltage_degradation": {"battery"},
}


def _scenario_supported(bundle: dict, scenario: str) -> bool:
    capabilities = set(bundle.get("capability_signals", []))
    return SCENARIO_SIGNAL_REQUIREMENTS.get(scenario, set()).issubset(capabilities)


def _window_is_truth(window: dict, truth_start: int, truth_end: int, min_overlap_fraction: float) -> bool:
    overlap = max(0, min(window["end_index"], truth_end) - max(window["start_index"], truth_start) + 1)
    length = max(1, window["end_index"] - window["start_index"] + 1)
    return overlap / length >= min_overlap_fraction


def _safe_ratio(a: int, b: int) -> float:
    return float(a / b) if b else 0.0


def validate_trained_model(bundle: dict, sessions: Iterable[TrainingSession]) -> dict:
    sessions = list(sessions)
    if not sessions:
        raise ValueError("At least one untouched final-test session is required for trained-model validation.")

    overlap_fraction = float(bundle.get("truth_overlap_fraction", 0.50))
    detector_thresholds = bundle.get("detector_thresholds", {})

    # Normal FPR is measured only once on untouched final-test sessions.
    normal_counts = {"fp": 0, "tn": 0}
    detector_normal = {k: {"fp": 0, "tn": 0} for k in DETECTOR_NAMES}
    for session in sessions:
        normal = score_with_trained_model(session.frame, session.session_id + "-test-normal", bundle)
        for w in normal.get("windows", []):
            if w["is_anomaly"]: normal_counts["fp"] += 1
            else: normal_counts["tn"] += 1
            for k in DETECTOR_NAMES:
                pred = bool(w["components"].get(k, 0.0) >= float(detector_thresholds.get(k, 1.1)))
                if pred: detector_normal[k]["fp"] += 1
                else: detector_normal[k]["tn"] += 1

    # Controlled perturbation campaign. Metrics are reported by severity and scenario.
    overall = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    per_case: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {
        "tp": 0, "fp": 0, "fn": 0, "tn": 0, "skipped": 0, "experiments": 0, "detected_experiments": 0
    })
    per_severity: dict[str, dict[str, int]] = defaultdict(lambda: {
        "tp": 0, "fp": 0, "fn": 0, "tn": 0, "experiments": 0, "detected_experiments": 0
    })
    detector_fault = {k: {"tp": 0, "fn": 0} for k in DETECTOR_NAMES}
    latencies: list[int] = []

    for session in sessions:
        for scenario in VALIDATION_SCENARIOS:
            if not _scenario_supported(bundle, scenario):
                for severity in SEVERITIES:
                    per_case[(scenario, severity)]["skipped"] += 1
                continue
            for severity in SEVERITIES:
                case = per_case[(scenario, severity)]
                try:
                    faulted = inject_fault(session.frame, scenario, severity=severity)
                except ValueError:
                    case["skipped"] += 1
                    continue
                start, end = fault_bounds(len(faulted))
                scored = score_with_trained_model(faulted, f"{session.session_id}-{scenario}-{severity}-test", bundle)
                windows = scored.get("windows", [])
                if not windows:
                    case["skipped"] += 1
                    continue

                case["experiments"] += 1
                per_severity[severity]["experiments"] += 1
                experiment_hit = False
                first_hit = None

                for w in windows:
                    truth = _window_is_truth(w, start, end, overlap_fraction)
                    pred = bool(w["is_anomaly"])
                    if truth and pred:
                        overall["tp"] += 1; case["tp"] += 1; per_severity[severity]["tp"] += 1
                        experiment_hit = True
                        if first_hit is None:
                            first_hit = max(0, w["start_index"] - start)
                    elif truth and not pred:
                        overall["fn"] += 1; case["fn"] += 1; per_severity[severity]["fn"] += 1
                    elif not truth and pred:
                        overall["fp"] += 1; case["fp"] += 1; per_severity[severity]["fp"] += 1
                    else:
                        overall["tn"] += 1; case["tn"] += 1; per_severity[severity]["tn"] += 1

                    if truth:
                        for k in DETECTOR_NAMES:
                            dpred = bool(w["components"].get(k, 0.0) >= float(detector_thresholds.get(k, 1.1)))
                            if dpred: detector_fault[k]["tp"] += 1
                            else: detector_fault[k]["fn"] += 1

                if experiment_hit:
                    case["detected_experiments"] += 1
                    per_severity[severity]["detected_experiments"] += 1
                    if first_hit is not None: latencies.append(first_hit)

    precision = _safe_ratio(overall["tp"], overall["tp"] + overall["fp"])
    recall = _safe_ratio(overall["tp"], overall["tp"] + overall["fn"])
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    normal_fpr = _safe_ratio(normal_counts["fp"], normal_counts["fp"] + normal_counts["tn"])

    scenario_results = []
    for (scenario, severity), c in sorted(per_case.items()):
        scenario_results.append({
            "scenario": scenario,
            "severity": severity,
            **c,
            "window_recall": round(_safe_ratio(c["tp"], c["tp"] + c["fn"]), 4),
            "injected_run_detection_rate": round(_safe_ratio(c["detected_experiments"], c["experiments"]), 4),
            "campaign_nontruth_fpr": round(_safe_ratio(c["fp"], c["fp"] + c["tn"]), 4),
        })

    severity_results = []
    for severity in SEVERITIES:
        c = per_severity[severity]
        severity_results.append({
            "severity": severity,
            **c,
            "window_recall": round(_safe_ratio(c["tp"], c["tp"] + c["fn"]), 4),
            "injected_run_detection_rate": round(_safe_ratio(c["detected_experiments"], c["experiments"]), 4),
        })

    detector_results = []
    for k in DETECTOR_NAMES:
        n = detector_normal[k]; f = detector_fault[k]
        detector_results.append({
            "detector": k,
            "threshold": detector_thresholds.get(k),
            "final_test_normal_fpr": round(_safe_ratio(n["fp"], n["fp"] + n["tn"]), 4),
            "injected_window_recall": round(_safe_ratio(f["tp"], f["tp"] + f["fn"]), 4),
        })

    total_experiments = sum(c["experiments"] for c in per_severity.values())
    detected_experiments = sum(c["detected_experiments"] for c in per_severity.values())
    return {
        "campaign": "untouched-final-test-plus-severity-controlled-injection-v0.3",
        "model_version": bundle.get("model_version"),
        "final_test_sessions": len(sessions),
        "capability_signals": bundle.get("capability_signals", []),
        "truth_window_overlap_fraction": overlap_fraction,
        "untouched_normal": {
            **normal_counts,
            "false_positive_rate": round(normal_fpr, 4),
        },
        "controlled_injection_window_level": {
            **overall,
            "precision": round(precision, 4),
            "recall_detection_rate": round(recall, 4),
            "f1": round(f1, 4),
        },
        "controlled_injection_run_level": {
            "experiments": total_experiments,
            "detected_experiments": detected_experiments,
            "detection_rate": round(_safe_ratio(detected_experiments, total_experiments), 4),
        },
        "severity_results": severity_results,
        "scenario_results": scenario_results,
        "detector_results": detector_results,
        "median_detection_latency_samples": float(np.median(latencies)) if latencies else None,
        "validation_policy": "Final metrics use vehicles never used for fitting, score normalization, weight selection, or threshold calibration. Synthetic severity labels are retained only by the validation harness, never passed to the detector.",
        "claim_boundary": "Controlled synthetic perturbations measure anomaly sensitivity, not real-world component-failure diagnostic accuracy or remaining useful life.",
    }
