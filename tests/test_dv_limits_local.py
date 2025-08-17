"""
Local-only sanity checks for Δv suggestions (NOT run in CI).

Checks:
- For each actor ('a' and 'b'), we get both prograde and retrograde suggestions,
  i.e., suggested_dv_mps contains one positive and one negative value.
- Magnitudes are capped by max_dv_mps and strictly > 0.
- Achieved separation follows Δs ≈ |Δv| * Δt / 1000 (km).
- Plan time is before TCA (dt_to_tca_s > 0).

This test is skipped automatically on CI (GitHub Actions).
"""

import os
import numpy as np
import pandas as pd
import pytest

# Skip the whole file if running in CI
if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
    pytest.skip("Local-only DV limits test (skipped on CI)", allow_module_level=True)

from ca_proto.dv_planner import plan_dv_for_refined


def test_dv_limits_and_directions_local():
    # Synthetic refined result with a TCA 15 minutes after plan time
    refined = pd.DataFrame([{
        "a": "SAT-A",
        "b": "SAT-B",
        "tca_utc": "2025-01-01T00:15:00Z",
        "dca_km": 0.2,
        "vrel_kms": 7.5,
        "t_index": 0,
        "t_idx_refined": 0,
    }])

    plan_time = "2025-01-01T00:00:00Z"
    target_dca_km = 10.0
    max_dv_mps = 0.02  # set a clear cap for the test

    out = plan_dv_for_refined(
        refined_df=refined,
        plan_time_iso=plan_time,
        target_dca_km=target_dca_km,
        max_dv_mps=max_dv_mps,
    )

    # Expect 4 rows: (actor a/b) × (prograde/retrograde)
    assert len(out) == 4

    # Per-actor checks
    for actor in ("a", "b"):
        sub = out[out["actor"] == actor]
        assert len(sub) == 2, f"Expected two suggestions for actor {actor}"

        dv = sub["suggested_dv_mps"].to_numpy(dtype=float)
        # Opposite signs (one >0, one <0)
        assert np.any(dv > 0) and np.any(dv < 0), f"{actor}: need both prograde (+) and retrograde (-)"

        # Magnitude capping and positivity (strictly > 0)
        mags = np.abs(dv)
        assert np.all(mags > 0), f"{actor}: Δv magnitudes must be > 0"
        assert np.allclose(mags, max_dv_mps), f"{actor}: Δv magnitudes should hit the cap {max_dv_mps} m/s"

        # Physics: achieved ≈ |dv| * dt / 1000
        dt = sub["dt_to_tca_s"].to_numpy(dtype=float)
        achieved = sub["achieved_dca_km"].to_numpy(dtype=float)
        expected = mags * dt / 1000.0
        assert np.allclose(achieved, expected, atol=1e-6), f"{actor}: achieved DCA mismatch"

        # dt must be positive (plan time before TCA)
        assert np.all(dt > 0), f"{actor}: dt_to_tca_s must be > 0"

