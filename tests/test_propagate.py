from ca_proto.tle_io import load_tles
from ca_proto.propagate import propagate_group

def test_propagate_shapes():
    df = load_tles("data/sample_tles.txt")
    states = propagate_group(df, "2025-08-16T00:00:00Z", "2025-08-16T00:05:00Z", step_s=60)
    # pick first sat
    name = next(iter(states.keys()))
    sat_df = states[name]
    assert {"time","rx_km","ry_km","rz_km","vx_kms","vy_kms","vz_kms"}.issubset(set(sat_df.columns))
    assert len(sat_df) == 6  # 0..5 minutes inclusive at 60s step

