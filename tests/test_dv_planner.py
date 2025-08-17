"""
Tests for the Δv planner heuristic (plan_dv_for_refined).

Scenario:
- Build a tiny refined_df with two pairs:
  1) Pair P1 (A vs B) with TCA 10 minutes after the plan time.
     - target_dca_km = 5.0, max_dv_mps = 0.01
     - dt = 600 s, so achieved_km = min(target, max_dv*dt/1000) = min(5.0, 0.01*600/1000) = 0.006 km
     - Expect FOUR suggestions (A/B actors × prograde/retrograde) with |Δv| = 0.01 m/s and achieved_dca_km ≈ 0.006.
  2) Pair P2 (C vs D) with TCA BEFORE plan time (too late).
     - Expect ZERO suggestions for this pair.
Checks:
- Number of rows, actors present, signs (+/-), magnitude capped by max_dv_mps.
- Achieved DCA matches Δs≈Δv·Δt / 1000.
- No rows emitted for pairs with plan_time >= TCA.
"""

import pandas as pd
import numpy as np

from ca_proto.dv_planner import plan_dv_for_refined


def test_dv_planner_basic_and_capping():
    # Synthetic refined results: two pairs with minimal required columns
    refined = pd.DataFrame(
        [
            {
                "a": "SAT-A",
                "b": "SAT-B",
                "tca_utc": "2025-01-01T00:10:00Z",
                "dca_km": 0.5,
                "vrel_kms": 7.5,
                "t_index": 0,
                "t_idx_refined": 0,
            },
            {
                "a": "SAT-C",
                "b": "SAT-D",
                "tca_utc": "2025-01-01T00:00:00Z",  # before plan time (will be skipped)
                "dca_km": 0.8,
                "vrel_kms": 7.2,
                "t_index": 0,
                "t_idx_refined": 0,
            },
        ]
    )

    plan_time = "2025-01-01T00:00:00Z"  # 10 minutes before P1's TCA
    target_dca_km = 5.0
    max_dv_mps = 0.01

    out = plan_dv_for_refined(
        refined_df=refined,
        plan_time_iso=plan_time,
        target_dca_km=target_dca_km,
        max_dv_mps=max_dv_mps,
    )

    # Expect only P1 to produce suggestions: 2 actors × 2 directions = 4 rows
    assert len(out) == 4, f"Expected 4 suggestions, got {len(out)}"

    # All rows should refer to the same pair (SAT-A/SAT-B)
    assert set(out["a"]) == {"SAT-A"}
    assert set(out["b"]) == {"SAT-B"}

    # Both actors must be present
    assert set(out["actor"]) == {"a", "b"}

    # Signs: prograde (+) and retrograde (-) should both appear
    mags = out["suggested_dv_mps"].to_numpy()
    assert np.any(mags > 0) and np.any(mags < 0), "Both + and - Δv suggestions expected"

    # Magnitudes must be capped at max_dv_mps
    assert np.allclose(np.abs(mags), max_dv_mps), "Δv magnitudes should equal max_dv_mps when capped"

    # Check achieved separation matches Δs≈Δv·Δt (km)
    tca = pd.to_datetime(refined.iloc[0]["tca_utc"], utc=True)
    tplan = pd.to_datetime(plan_time, utc=True)
    dt_s = (tca - tplan).total_seconds()
    expected_km = (max_dv_mps * dt_s) / 1000.0  # 0.01 m/s * 600 s / 1000 = 0.006 km
    assert np.allclose(out["achieved_dca_km"].to_numpy(), expected_km), "achieved_dca_km should match Δv*Δt/1000"

    # Ensure no suggestions for the pair with TCA before plan time
    assert not ((out["a"] == "SAT-C") | (out["b"] == "SAT-D")).any(), "No rows should be emitted for late TCA pairs"

