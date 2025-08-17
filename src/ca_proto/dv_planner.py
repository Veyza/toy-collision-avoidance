from __future__ import annotations
from typing import List, Dict, Optional
import math
import pandas as pd

def _parse_time(ts: str) -> pd.Timestamp:
    # Parse an ISO8601 string into a pandas.Timestamp (with UTC timezone).
    return pd.to_datetime(ts, utc=True)

def _suggest_for_actor(
    a: str,
    b: str,
    tca_iso: str,
    actor: str,                 # "a" or "b": which satellite is maneuvering
    plan_time_iso: str,         # when the maneuver is planned
    target_dca_km: float,       # desired miss distance (km)
    max_dv_mps: float,          # max allowed Δv magnitude (m/s)
) -> List[Dict[str, object]]:
    """
    Make two along-track maneuver suggestions (prograde and retrograde) for one actor.

    Simplified toy model:
    - Assumes linear build-up of along-track separation: Δs ≈ Δv * Δt
      (Δs in meters, Δv in m/s, Δt in seconds).
    - Ignores orbital dynamics, covariance, eccentricity, inclination, J2, etc.
    - Useful only for illustrative "what-if" planning.

    Returns a list of dicts describing the two options.
    """
    # Parse planning and TCA times
    t_plan = _parse_time(plan_time_iso)
    t_tca  = _parse_time(tca_iso)
    dt_s   = (t_tca - t_plan).total_seconds()  # time available until TCA in seconds

    if dt_s <= 0:
        # If planning time is at/after TCA, no maneuver can affect this encounter
        return []

    # Compute the Δv required to achieve target miss distance in given time
    dv_needed_mps = (target_dca_km * 1000.0) / dt_s
    # Limit it by the maximum allowed capability
    dv_cap_mps = min(abs(dv_needed_mps), max_dv_mps)

    # Compute how much separation is actually achieved with capped Δv
    achieved_km = (dv_cap_mps * dt_s) / 1000.0

    suggestions = []
    for sign, direction in [(+1.0, "prograde"), (-1.0, "retrograde")]:
        # Generate both options: positive Δv (prograde) and negative Δv (retrograde)
        suggestions.append({
            "a": a,
            "b": b,
            "actor": actor,  # which satellite performs the maneuver
            "t_plan_utc": t_plan.isoformat(),
            "tca_utc": t_tca.isoformat(),
            "dt_to_tca_s": round(dt_s, 3),
            "target_dca_km": float(target_dca_km),
            "suggested_dv_mps": round(sign * dv_cap_mps, 6),
            "achieved_dca_km": round(achieved_km, 6),
            "note": "Δs≈Δv·Δt; toy heuristic (no covariance/a,e,i/J2).",
        })
    return suggestions

def plan_dv_for_refined(
    refined_df: pd.DataFrame,
    plan_time_iso: str,
    target_dca_km: float = 2.0,   # default 2 km target separation
    max_dv_mps: float = 0.05,     # default maneuver cap 5 cm/s
) -> pd.DataFrame:
    """
    For each refined conjunction pair, propose four toy maneuvers:
    - 2 for satellite A (prograde/retrograde)
    - 2 for satellite B (prograde/retrograde)

    Skips any encounters that are already in the past (plan_time >= TCA).

    Returns a DataFrame with maneuver options, columns:
      a, b, actor, t_plan_utc, tca_utc, dt_to_tca_s,
      target_dca_km, suggested_dv_mps, achieved_dca_km, note
    """
    rows: List[Dict[str, object]] = []
    for _, r in refined_df.iterrows():
        a = str(r["a"]); b = str(r["b"])
        tca_iso = str(r["tca_utc"])

        # Generate suggestions for both actors
        rows.extend(_suggest_for_actor(a, b, tca_iso, actor="a",
                                       plan_time_iso=plan_time_iso,
                                       target_dca_km=target_dca_km,
                                       max_dv_mps=max_dv_mps))
        rows.extend(_suggest_for_actor(a, b, tca_iso, actor="b",
                                       plan_time_iso=plan_time_iso,
                                       target_dca_km=target_dca_km,
                                       max_dv_mps=max_dv_mps))
    cols = ["a","b","actor","t_plan_utc","tca_utc","dt_to_tca_s",
            "target_dca_km","suggested_dv_mps","achieved_dca_km","note"]
    return pd.DataFrame(rows, columns=cols).sort_values(
        ["tca_utc","a","b","actor","suggested_dv_mps"]
    ).reset_index(drop=True)

