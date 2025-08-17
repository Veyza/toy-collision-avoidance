import numpy as np
import pandas as pd
from ca_proto.geometry import _extract_positions, pairwise_min_distance

def _mk_df(times, xyz):
    return pd.DataFrame({
        "time": times,
        "rx_km": xyz[:,0], "ry_km": xyz[:,1], "rz_km": xyz[:,2],
        "vx_kms": 0.0, "vy_kms": 0.0, "vz_kms": 0.0,
    })

def test_pairwise_min_distance_simple():
    times = pd.date_range("2025-01-01T00:00:00Z", periods=5, freq="60s", tz="UTC")
    # sat A at origin
    A = np.zeros((5,3))
    # sat B moving from 10 km to 2 km away in x
    B = np.array([[10,0,0],[8,0,0],[6,0,0],[4,0,0],[2,0,0]], dtype=float)

    states = {
        "A": _mk_df(times, A),
        "B": _mk_df(times, B),
    }
    names, R, ts = _extract_positions(states)
    pairs = pairwise_min_distance(names, R)
    assert len(pairs) == 1
    a, b, dmin, idx = pairs[0]
    assert {a,b} == {"A","B"}
    assert idx == 4
    assert abs(dmin - 2.0) < 1e-6

