import numpy as np
import pandas as pd
from ca_proto.screening import coarse_screen

def _mk_df(times, xyz):
    return pd.DataFrame({
        "time": times,
        "rx_km": xyz[:,0], "ry_km": xyz[:,1], "rz_km": xyz[:,2],
        "vx_kms": 0.0, "vy_kms": 0.0, "vz_kms": 0.0,
    })

def test_coarse_screen_threshold():
    times = pd.date_range("2025-01-01T00:00:00Z", periods=4, freq="60s", tz="UTC")
    A = np.zeros((4,3))
    B = np.array([[6,0,0],[5,0,0],[4,0,0],[3,0,0]], dtype=float)
    states = {"A": _mk_df(times, A), "B": _mk_df(times, B)}
    # screen at 4.5 km → we should keep (min=3 km)
    df = coarse_screen(states, screen_km=4.5)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["a"] == "A" or row["b"] == "A"
    assert row["dmin_km"] == 3.0

def test_coarse_screen_empty_result():
    import numpy as np, pandas as pd
    times = pd.date_range("2025-01-01T00:00:00Z", periods=3, freq="60s", tz="UTC")
    A = np.zeros((3,3))
    B = np.array([[1000,0,0],[1000,0,0],[1000,0,0]], dtype=float)
    def _mk_df(xyz):
        return pd.DataFrame({
            "time": times,
            "rx_km": xyz[:,0], "ry_km": xyz[:,1], "rz_km": xyz[:,2],
            "vx_kms": 0.0, "vy_kms": 0.0, "vz_kms": 0.0,
        })
    states = {"A": _mk_df(A), "B": _mk_df(B)}
    df = coarse_screen(states, screen_km=10.0)
    assert list(df.columns) == ["a","b","dmin_km","t_index","time_utc"]
    assert df.empty

