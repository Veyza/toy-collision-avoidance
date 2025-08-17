"""
Tests for conjunction refinement.

Covers:
- Refined closest-approach search with interpolation/upsampling.
- Correct identification of TCA (time of closest approach).
- Handling of relative motion and distance minimization.
"""

import numpy as np
import pandas as pd
from ca_proto.refine import refine_pair

def _mk_df(times, xyz, vxyz):
    n = len(times)
    return pd.DataFrame({
        "time": times,
        "rx_km": xyz[:,0], "ry_km": xyz[:,1], "rz_km": xyz[:,2],
        "vx_kms": np.full(n, vxyz[0]),
        "vy_kms": np.full(n, vxyz[1]),
        "vz_kms": np.full(n, vxyz[2]),
    })

def test_refine_pair_linear_motion():
    times = pd.date_range("2025-01-01T00:00:00Z", periods=11, freq="10s", tz="UTC")
    t = np.arange(11) * 10.0  # seconds

    # A at origin, stationary
    A_pos = np.zeros((11,3))
    A_vel = (0.0, 0.0, 0.0)

    # B starts at x=5 km, moves towards origin at 0.5 km/s along -x
    B_pos = np.stack([5.0 - 0.5*(t), np.zeros_like(t), np.zeros_like(t)], axis=1)
    B_vel = (-0.5, 0.0, 0.0)

    dfA = _mk_df(times, A_pos, A_vel)
    dfB = _mk_df(times, B_pos, B_vel)

    # Coarse grid TCA is between samples near t = 10 s
    res = refine_pair(dfA, dfB, window=2, upsample=20)
    # true TCA at x=0 → t = 10 s
    assert abs(pd.to_datetime(res["tca_utc"]) - times[1]) < pd.Timedelta(seconds=1)
    assert abs(res["dca_km"] - 0.0) < 1e-3
    assert abs(res["vrel_kms"] - 0.5) < 1e-6

