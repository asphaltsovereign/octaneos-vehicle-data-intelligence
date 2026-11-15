"""Train Sentinel V3.3 with session-robust calibration and a new vehicle lockbox split."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.ingestion import ingest_csv_bytes  # noqa: E402
from app.services.training import TrainingSession, train_baseline_model  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepared-dir", default="data/prepared_ved")
    ap.add_argument("--output-dir", default="artifacts/sentinel_baseline_v32")
    ap.add_argument("--max-sessions", type=int, default=80)
    ap.add_argument("--target-normal-fpr", type=float, default=0.02)
    ap.add_argument("--calibration-guard-quantile", type=float, default=0.90)
    args = ap.parse_args()

    sessions = []
    for path in sorted(Path(args.prepared_dir).glob("VED-*-TRIP-*.csv"))[: args.max_sessions]:
        raw = path.read_bytes()
        s = ingest_csv_bytes(raw)
        if not s.analysis_ready or s.quality_score < 75:
            continue
        sessions.append(TrainingSession(s.session_id, s.vehicle_id, s.frame, s.file_hash))

    manifest = train_baseline_model(
        sessions, output_dir=args.output_dir, target_normal_fpr=args.target_normal_fpr,
        calibration_guard_quantile=args.calibration_guard_quantile
    )
    print("SENTINEL V3.3 BASELINE TRAINED + SESSION-ROBUST CALIBRATION")
    keys = [
        "model_version", "training_sessions", "calibration_sessions", "test_sessions",
        "training_vehicles", "calibration_vehicles", "test_vehicles",
        "training_windows", "calibration_windows", "test_windows", "feature_count",
        "decision_threshold", "pca_explained_variance", "capability_signals",
    ]
    for key in keys:
        print(f"{key}: {manifest[key]}")
    cal = manifest["calibration"]
    print(f"calibration_target_normal_fpr: {cal['target_normal_fpr']:.4f}")
    print(f"calibration_achieved_normal_fpr: {cal['calibration_normal_fpr']:.4f}")
    print(f"calibration_session_fpr_p90: {cal['calibration_session_fpr_p90']:.4f}")
    print(f"calibration_injected_positive_recall: {cal['calibration_injected_positive_recall']:.4f}")
    print(f"calibration_injected_run_detection_rate: {cal['calibration_injected_run_detection_rate']:.4f}")
    print(f"ensemble_weights: {manifest['ensemble_weights']}")
    print(f"artifact: {manifest['artifact_paths']['bundle']}")
    print(f"manifest: {manifest['artifact_paths']['manifest']}")


if __name__ == "__main__":
    main()
