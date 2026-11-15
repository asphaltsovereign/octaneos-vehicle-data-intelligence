"""Evaluate Sentinel V3.2 on untouched final-test vehicles plus controlled severity injections."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.ingestion import ingest_csv_bytes  # noqa: E402
from app.services.model_store import load_bundle  # noqa: E402
from app.services.training import TrainingSession  # noqa: E402
from app.services.trained_validation import validate_trained_model  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepared-dir", default="data/prepared_ved")
    ap.add_argument("--model-dir", default="artifacts/sentinel_baseline_v32")
    ap.add_argument("--output", default="artifacts/sentinel_baseline_v32/final_test_report.json")
    args = ap.parse_args()

    bundle, manifest = load_bundle(args.model_dir)
    test_ids = set(manifest.get("test_session_ids", []))
    if not test_ids:
        raise SystemExit("Model manifest does not contain test_session_ids. Retrain with Sentinel V3.2.")

    sessions = []
    for path in sorted(Path(args.prepared_dir).glob("VED-*-TRIP-*.csv")):
        raw = path.read_bytes()
        s = ingest_csv_bytes(raw)
        if s.session_id in test_ids:
            sessions.append(TrainingSession(s.session_id, s.vehicle_id, s.frame, s.file_hash))
    if not sessions:
        raise SystemExit("No final-test trips were found in prepared-dir.")

    report = validate_trained_model(bundle, sessions)
    report["model_artifact_sha256"] = manifest.get("artifact_sha256")
    report["final_test_session_ids"] = sorted(s.session_id for s in sessions)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    w = report["controlled_injection_window_level"]
    r = report["controlled_injection_run_level"]
    print("SENTINEL V3.3 FINAL-TEST VALIDATION")
    print(f"final_test_sessions: {report['final_test_sessions']}")
    print(f"untouched_normal_fpr: {report['untouched_normal']['false_positive_rate']:.4f}")
    print(f"injected_window_precision: {w['precision']:.4f}")
    print(f"injected_window_recall: {w['recall_detection_rate']:.4f}")
    print(f"injected_window_f1: {w['f1']:.4f}")
    print(f"injected_run_detection_rate: {r['detection_rate']:.4f} ({r['detected_experiments']}/{r['experiments']})")
    print("severity:")
    for s in report["severity_results"]:
        print(f"  {s['severity']}: window_recall={s['window_recall']:.4f}, run_detection={s['injected_run_detection_rate']:.4f}")
    print("detectors:")
    for d in report["detector_results"]:
        print(f"  {d['detector']}: normal_fpr={d['final_test_normal_fpr']:.4f}, injected_recall={d['injected_window_recall']:.4f}")
    print(f"report: {out}")
    print(report["claim_boundary"])


if __name__ == "__main__":
    main()
