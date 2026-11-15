from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_demo_normal():
    r = client.post('/demo', json={'scenario': 'normal'})
    assert r.status_code == 200
    body = r.json()
    assert body['sample_count'] == 120
    assert 'Sentinel Ensemble' in body['model']['name']
    assert 0 <= body['health_score'] <= 100


def test_fault_scenario_runs():
    r = client.post(
        "/demo",
        json={"scenario": "rpm_instability", "severity": "medium"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body['anomaly_regions']) >= 1
    assert body["ground_truth"]["scenario"] == "rpm_instability"
    assert body["ground_truth"]["detected"] is True
    if body["model"]["runtime_mode"] == "frozen_trained_model":
        allowed = set(body["model"]["capability_signals"])
        assert all(
            signal in allowed
            for region in body["anomaly_regions"]
            for signal in region["top_signals"]
        )


def test_explain_without_key_falls_back(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    analysis = client.post("/demo", json={"scenario": "voltage_degradation"}).json()
    response = client.post("/explain", json={"analysis": analysis, "mode": "fast"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deterministic_fallback"
    assert data["provider"] == "local"
    assert data["executive_summary"]
