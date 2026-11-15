from pathlib import Path

from app.services.demo import demo_frame
from app.services.model_store import load_bundle
from app.services.simulator import inject_fault
from app.services.training import TrainingSession, score_with_trained_model, train_baseline_model
from app.services.trained_validation import validate_trained_model


def _sessions(n=10):
    sessions = []
    for i in range(n):
        f = demo_frame().copy()
        f["speed"] = f["speed"] * (0.90 + i * 0.018)
        f["rpm"] = f["rpm"] * (0.94 + i * 0.012)
        f["maf"] = f["maf"] * (0.92 + i * 0.015)
        f["engine_load"] = (f["engine_load"] * (0.94 + i * 0.008)).clip(0, 100)
        sessions.append(TrainingSession(f"S{i}", f"V{i}", f))
    return sessions


def test_training_writes_three_way_manifest_and_artifact(tmp_path: Path):
    manifest = train_baseline_model(_sessions(), output_dir=tmp_path, window_size=16, stride=8)
    assert manifest["training_windows"] > 0
    assert manifest["calibration_windows"] > 0
    assert manifest["test_windows"] > 0
    assert manifest["feature_count"] >= 8
    assert set(manifest["train_vehicle_ids"]).isdisjoint(manifest["calibration_vehicle_ids"])
    assert set(manifest["train_vehicle_ids"]).isdisjoint(manifest["test_vehicle_ids"])
    assert set(manifest["calibration_vehicle_ids"]).isdisjoint(manifest["test_vehicle_ids"])
    bundle, disk_manifest = load_bundle(tmp_path)
    assert bundle["model_version"] == manifest["model_version"]
    assert disk_manifest["artifact_sha256"]
    assert 0 <= manifest["calibration"]["calibration_normal_fpr"] <= 0.08


def test_trained_model_scores_unseen_session(tmp_path: Path):
    train_baseline_model(_sessions(), output_dir=tmp_path, window_size=16, stride=8)
    bundle, _ = load_bundle(tmp_path)
    frame = inject_fault(demo_frame(), "rpm_instability", severity="severe")
    result = score_with_trained_model(frame, "TEST", bundle)
    assert result["status"] == "ok"
    assert result["window_count"] > 0
    assert all(0 <= w["score"] <= 1 for w in result["windows"])
    assert all("detector_flags" in w for w in result["windows"])


def test_final_test_validation_is_structured(tmp_path: Path):
    sessions = _sessions(12)
    manifest = train_baseline_model(sessions, output_dir=tmp_path, window_size=16, stride=8)
    bundle, _ = load_bundle(tmp_path)
    by_id = {s.session_id: s for s in sessions}
    final_test = [by_id[sid] for sid in manifest["test_session_ids"]]
    out = validate_trained_model(bundle, final_test)
    assert 0 <= out["untouched_normal"]["false_positive_rate"] <= 1
    assert 0 <= out["controlled_injection_window_level"]["recall_detection_rate"] <= 1
    assert 0 <= out["controlled_injection_run_level"]["detection_rate"] <= 1
    assert len(out["severity_results"]) == 3
    assert len(out["detector_results"]) == 3
    assert "not real-world" in out["claim_boundary"]
