from pathlib import Path

import numpy as np

from app.services.demo import demo_frame


def test_demo_drive_cycle_has_multiple_operating_phases_not_single_triangle():
    speed = demo_frame()["speed"].to_numpy(dtype=float)
    block_means = np.array([chunk.mean() for chunk in np.array_split(speed, 12)])
    directions = np.sign(np.diff(block_means))
    directions = directions[directions != 0]
    reversals = int(np.sum(directions[1:] != directions[:-1]))
    assert reversals >= 3, f"expected multi-phase drive cycle, got only {reversals} direction reversals"


def test_demo_drive_cycle_contains_stable_cruise_samples():
    speed = demo_frame()["speed"].to_numpy(dtype=float)
    deltas = np.abs(np.diff(speed))
    assert int(np.sum(deltas < 0.35)) >= 12, "demo needs visible cruise periods rather than a continuous ramp"


def test_command_center_copy_is_truthful_and_chart_is_unit_labelled():
    root = Path(__file__).resolve().parents[2]
    source = (root / "frontend" / "src" / "Legacy.tsx").read_text(encoding="utf-8")
    assert "A frozen multivariate model detects abnormal operating windows" not in source
    assert "SYNTHETIC DEMO TELEMETRY" in source
    assert "RPM (rev/min)" in source
    assert "Speed (km/h)" in source
    assert "Engine load (%)" in source
    assert "CONTROLLED FAULT INJECTION" in source


def test_command_center_uses_four_primary_metrics_and_no_zero_window_card():
    root = Path(__file__).resolve().parents[2]
    source = (root / "frontend" / "src" / "Legacy.tsx").read_text(encoding="utf-8")
    assert 'className="cards four"' in source
    assert 'label="MODEL WINDOWS"' not in source
    assert 'label="SCREENING STATUS"' in source


def test_fault_lab_and_model_card_do_not_claim_frozen_runtime_when_missing():
    root = Path(__file__).resolve().parents[2]
    source = (root / "frontend" / "src" / "Legacy.tsx").read_text(encoding="utf-8")
    assert "Same frozen pipeline" not in source
    assert "OUTSIDE FROZEN MODEL CAPABILITY" not in source
    assert "SAME SCREENING PIPELINE" in source
    assert "SCENARIO CAPABILITY GATED" in source
    assert "RUNTIME ARTIFACT NOT PACKAGED" in source
