from __future__ import annotations

from collections import Counter
import numpy as np
import pandas as pd

from .rules import compute_metrics, run_engineering_rules

UNSUPPORTED_WITH_CURRENT_SIGNALS = {
    "injector health": "Injector-specific diagnosis requires validated injector/AFR/fuel-pressure evidence.",
    "ignition timing": "Ignition timing requires a validated timing/ECU signal.",
    "ecu fault code": "DTC/ECU diagnosis requires actual ECU communication data.",
    "ethanol percentage": "Ethanol percentage requires a validated ethanol-content sensor signal.",
    "afr": "AFR diagnosis requires a validated wideband oxygen/AFR signal.",
}


def _risk_rank(value: str) -> int:
    return {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}.get(value, 0)


def _metric_evidence(metrics: dict, keys: list[str]) -> list[dict]:
    out = []
    for key in keys:
        if key in metrics and metrics[key] is not None:
            out.append({"signal": key, "observation": f"Observed {key.replace('_', ' ')} = {metrics[key]}", "value": float(metrics[key]) if isinstance(metrics[key], (int, float)) else None, "direction": "support"})
    return out


def investigate(frame: pd.DataFrame, source: str, anomaly: dict, quality_score: int) -> dict:
    metrics = compute_metrics(frame)
    rules = run_engineering_rules(frame, source, metrics)
    hypotheses: list[dict] = []

    anomaly_signals = Counter(sig.split("_roll")[0].split("_gradient")[0].split("_delta")[0] for r in anomaly.get("regions", []) for sig in r.get("top_signals", []))
    anomaly_peak = max([r["score"] for r in anomaly.get("regions", [])], default=0.0)

    def add_hypothesis(name, subsystem, severity, confidence, signals, action, contradictions=None):
        evidence = _metric_evidence(metrics, signals)
        evidence.extend({"signal": s, "observation": f"{s} repeatedly appears among dominant anomaly contributors.", "direction": "support"} for s, c in anomaly_signals.items() if s in signals and c > 0)
        hypotheses.append({
            "name": name,
            "subsystem": subsystem,
            "severity": severity,
            "confidence": round(min(max(confidence, 0.0), 0.98), 3),
            "evidence": evidence,
            "contradictions": contradictions or [],
            "recommended_action": action,
            "blocked_claims": [],
        })

    for rule in rules:
        if rule["id"] in {"MOVING_UNDERVOLTAGE", "MOVING_OVERVOLTAGE"}:
            add_hypothesis(
                "Electrical supply instability",
                "electrical",
                rule["severity"],
                rule["confidence"] + 0.15 * ("battery" in anomaly_signals),
                ["moving_battery", "min_battery"],
                "Verify battery-terminal and charging-system voltage with a calibrated meter under controlled conditions.",
            )

    if "battery" in anomaly_signals and anomaly_peak >= 0.7 and not any(h["subsystem"] == "electrical" for h in hypotheses):
        add_hypothesis(
            "Abnormal voltage behaviour",
            "electrical",
            "medium",
            0.55 + 0.25 * anomaly_peak,
            ["median_battery", "min_battery"],
            "Inspect the voltage trace and confirm with independent measurement before replacing components.",
        )

    if "temp" in anomaly_signals and anomaly_peak >= 0.7:
        contradiction = []
        if metrics.get("max_temp") is not None and metrics["max_temp"] < 45:
            contradiction.append({"signal": "max_temp", "observation": "Absolute temperature remains modest; anomaly may be trend-related rather than overheating.", "value": metrics["max_temp"], "direction": "contradict"})
        add_hypothesis(
            "Abnormal thermal trend",
            "thermal",
            "medium",
            0.5 + 0.25 * anomaly_peak,
            ["avg_temp", "max_temp"],
            "Review sensor placement and compare the thermal slope against a known baseline before inferring overheating.",
            contradiction,
        )

    if "rpm" in anomaly_signals and anomaly_peak >= 0.7:
        add_hypothesis(
            "RPM behaviour deviation",
            "operation",
            "low",
            0.48 + 0.2 * anomaly_peak,
            ["avg_rpm", "max_rpm"],
            "Compare RPM behaviour against speed/load context; do not infer ignition or injector faults without additional signals.",
        )

    if not hypotheses and anomaly.get("regions"):
        top = anomaly["regions"][0]
        add_hypothesis(
            "Unclassified telemetry anomaly",
            "telemetry",
            "low",
            0.45 + 0.25 * top["score"],
            [],
            "Inspect the highlighted telemetry window and compare with another session before making a component-level diagnosis.",
        )

    limitations = [
        "Public VED data validates software behaviour only; it is not Yamaha R15 V2 health evidence." if source == "ved" else "SAN-V1 results remain screening evidence until the hardware and vehicle installation are independently validated.",
        "The anomaly model detects statistical deviation; it does not identify a failed component by itself.",
        "No ECU/DTC, AFR, injector, ignition-timing or ethanol-content claim is made unless those validated signals are present.",
    ]

    # Explicit safety-agent output: record blocked unsupported claims.
    blocked = list(UNSUPPORTED_WITH_CURRENT_SIGNALS.values())
    if hypotheses:
        hypotheses[0]["blocked_claims"] = blocked

    highest = max([_risk_rank(h["severity"]) for h in hypotheses], default=0)
    anomaly_component = min(35, round(len(anomaly.get("regions", [])) * 3 + anomaly_peak * 18))
    quality_penalty = round((100 - quality_score) * 0.18)
    health = max(0, min(100, 100 - anomaly_component - quality_penalty - highest * 6))
    risk = ["info", "low", "medium", "high", "critical"][min(highest, 4)]
    if len(anomaly.get("regions", [])) >= 6 and highest < 2:
        risk = "medium"

    return {
        "metrics": metrics,
        "rules": rules,
        "hypotheses": sorted(hypotheses, key=lambda x: x["confidence"], reverse=True),
        "limitations": limitations,
        "health_score": int(health),
        "risk": risk,
    }
