from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_demo_exposes_visualization_and_provenance_fields():
    response = client.post(
        "/demo",
        json={"scenario": "signal_spikes", "severity": "severe"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["telemetry"]
    assert body["signal_coverage"]["speed"] == 1.0
    assert body["ground_truth"]["label_hidden_from_model"] is True
    assert body["ground_truth"]["severity"] == "severe"
    assert body["provenance"]["raw_file_retained"] is False
    assert "component-failure" in body["claim_boundary"]


def test_scenario_catalog_declares_capability_requirements():
    body = client.get("/scenarios").json()
    catalog = {item["id"]: item for item in body["catalog"]}
    assert catalog["rpm_instability"]["requires"] == ["rpm"]
    assert catalog["voltage_degradation"]["requires"] == ["battery"]
    assert set(body["scenarios"]) >= {"normal", "rpm_instability", "signal_spikes"}


def test_ai_status_is_safe_to_show_in_ui(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "never-return-this")
    body = client.get("/ai/status").json()
    assert body["configured"] is True
    assert body["raw_telemetry_shared"] is False
    assert "never-return-this" not in str(body)


def test_submission_status_maps_required_evidence():
    body = client.get("/submission/status").json()
    labels = {item["item"] for item in body["submission_items"]}
    assert {
        "Source code",
        "README and reproducibility guide",
        "Presentation",
        "3-5 minute demo video",
    } <= labels
    assert body["truth_boundary"]


def test_invalid_severity_is_rejected():
    response = client.post(
        "/demo",
        json={"scenario": "rpm_instability", "severity": "extreme"},
    )
    assert response.status_code == 422


def test_built_frontend_is_served_when_present():
    response = client.get("/")
    assert response.status_code == 200
    assert "OctaneOS Sentinel" in response.text
