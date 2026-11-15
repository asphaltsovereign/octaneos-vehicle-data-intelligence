import pandas as pd

from app.services.ingestion import ingest_csv_bytes
from app.services.windowing import build_window_matrix


def test_real_ved_aliases_map_oat_maf_and_load():
    text = """DayNum,VehId,Trip,Timestamp(ms),Latitude[deg],Longitude[deg],Vehicle Speed[km/h],MAF[g/sec],Engine RPM[RPM],Absolute Load[%],OAT[DegC],Fuel Rate[L/hr],HV Battery Voltage[V],HV Battery SOC[%]\n1,8,706,0,42.2,-83.6,20,8.2,1500,35,22,,,\n1,8,706,1000,42.2,-83.6,22,8.8,1600,38,22.2,,,\n1,8,706,2000,42.2,-83.6,25,9.5,1700,42,22.3,,,\n1,8,706,3000,42.2,-83.6,28,10.2,1800,45,22.4,,,\n1,8,706,4000,42.2,-83.6,31,11.0,1900,49,22.5,,,\n"""
    s = ingest_csv_bytes(text.encode())
    assert s.frame["maf"].notna().all()
    assert s.frame["engine_load"].notna().all()
    assert s.frame["temp"].notna().all()


def test_window_matrix_contains_automotive_relationships():
    n = 32
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="1s", tz="UTC"),
        "speed": range(n),
        "rpm": [900 + i*45 for i in range(n)],
        "maf": [3 + i*0.2 for i in range(n)],
        "engine_load": [20 + i*0.8 for i in range(n)],
        "temp": [25.0]*n,
        "fuel_rate": [float("nan")]*n,
        "battery": [float("nan")]*n,
        "soc": [float("nan")]*n,
        "gps_fix": [1]*n,
    })
    x, _ = build_window_matrix(frame, "T", window_size=16, stride=8)
    assert "maf__mean" in x.columns
    assert "engine_load__mean" in x.columns
    assert "corr__rpm_maf" in x.columns
    assert "corr__rpm_load" in x.columns
    assert "corr__maf_load" in x.columns


def test_core_fault_scenarios_modify_powertrain_signals():
    from app.services.demo import demo_frame
    from app.services.simulator import inject_fault
    f = demo_frame()
    assert not inject_fault(f, "maf_drift")["maf"].equals(f["maf"])
    assert not inject_fault(f, "load_instability")["engine_load"].equals(f["engine_load"])
