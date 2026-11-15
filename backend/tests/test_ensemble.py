from app.services.demo import demo_frame
from app.services.simulator import inject_fault
from app.services.anomaly import run_anomaly_detection
from app.services.validation import run_validation_campaign


def test_ensemble_has_multiple_detectors():
    result = run_anomaly_detection(demo_frame())
    assert result["status"] == "ok"
    assert "IF+PCA" in result["model_name"]
    assert set(result["component_scores"]) == {"isolation_forest", "pca_reconstruction", "robust_z", "ewma", "cusum"}
    assert len(result["point_scores"]) == len(demo_frame())


def test_fault_scenario_produces_regions():
    frame = inject_fault(demo_frame(), "voltage_degradation")
    result = run_anomaly_detection(frame)
    assert result["regions"]
    assert 0 <= result["regions"][0]["score"] <= 1


def test_validation_campaign_is_honest_and_structured():
    out = run_validation_campaign(1)
    assert 0 <= out["detection_rate"] <= 1
    assert 0 <= out["false_positive_rate"] <= 1
    assert "Synthetic fault injection" in out["claim_boundary"]
