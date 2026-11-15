from fastapi.testclient import TestClient

from app.main import app


def test_model_info_endpoint_exists():
    client = TestClient(app)
    response = client.get('/model/info')
    assert response.status_code == 200
    body = response.json()
    assert 'available' in body


def test_demo_exposes_runtime_mode():
    client = TestClient(app)
    response = client.post('/demo', json={'scenario': 'normal'})
    assert response.status_code == 200
    body = response.json()
    assert 'runtime_mode' in body['model']


def test_capability_filter_blocks_sparse_signal_hypotheses():
    import numpy as np
    import pandas as pd
    from app.services.runtime_model import _window_signal_contributions

    class IdentityScaler:
        def transform(self, x):
            return x

    frame = pd.DataFrame([{
        "rpm__mean": 8.0,
        "battery__coverage": 1000.0,
    }])
    bundle = {
        "feature_columns": ["rpm__mean", "battery__coverage"],
        "fill_values": {"rpm__mean": 0.0, "battery__coverage": 0.0},
        "scaler": IdentityScaler(),
        "robust_center": np.array([0.0, 0.0]),
        "robust_scale": np.array([1.0, 1.0]),
        "capability_signals": ["rpm"],
    }
    out = _window_signal_contributions(frame, bundle)
    assert out == [["rpm"]]
