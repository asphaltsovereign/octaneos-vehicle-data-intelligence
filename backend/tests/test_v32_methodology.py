from app.services.demo import demo_frame
from app.services.simulator import fault_bounds, inject_fault
from app.services.training import TrainingSession, train_baseline_model


def test_fault_severity_ladder_increases_rpm_perturbation():
    f = demo_frame()
    start, end = fault_bounds(len(f))
    base = f.loc[start:end, "rpm"]
    mild = inject_fault(f, "rpm_instability", seed=7, severity="mild").loc[start:end, "rpm"]
    severe = inject_fault(f, "rpm_instability", seed=7, severity="severe").loc[start:end, "rpm"]
    mild_change = (mild - base).abs().mean()
    severe_change = (severe - base).abs().mean()
    assert severe_change > mild_change


def test_sparse_optional_signals_do_not_become_capabilities(tmp_path):
    sessions = []
    for i in range(10):
        f = demo_frame().copy()
        f["temp"] = float("nan")
        f["battery"] = float("nan")
        f["soc"] = float("nan")
        f["fuel_rate"] = float("nan")
        sessions.append(TrainingSession(f"S{i}", f"V{i}", f))
    manifest = train_baseline_model(sessions, output_dir=tmp_path)
    caps = set(manifest["capability_signals"])
    assert "rpm" in caps
    assert "maf" in caps
    assert "engine_load" in caps
    assert "temp" not in caps
    assert "battery" not in caps
