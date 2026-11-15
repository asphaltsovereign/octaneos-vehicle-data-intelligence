import numpy as np

from app.services.training import _session_guard_threshold, _weight_grid


def test_session_guard_threshold_is_conservative_to_outlier_session():
    a = np.linspace(0.0, 0.5, 100)
    b = np.linspace(0.0, 0.55, 100)
    c = np.linspace(0.0, 0.9, 100)
    per_session = [np.quantile(x, 0.98) for x in [a, b, c]]
    guarded = _session_guard_threshold([a, b, c], 0.02, 0.90)
    assert guarded >= np.median(per_session)
    assert guarded <= max(per_session)


def test_weight_grid_allows_zero_but_keeps_two_active_detectors():
    grid = _weight_grid()
    assert any(w["robust_z"] == 0.0 for w in grid)
    assert all(sum(v > 0 for v in w.values()) >= 2 for w in grid)
