from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd

def _coarse_min_index(df_a: pd.DataFrame, df_b: pd.DataFrame) -> int:
    """
    Find the coarse index of minimum separation distance between two satellites.

    Parameters
    ----------
    df_a, df_b : pd.DataFrame
        Trajectory data for satellites A and B, with columns rx_km, ry_km, rz_km.

    Returns
    -------
    idx : int
        Index of the timestep (coarse grid) where the two satellites are closest.
    """
    # Relative position vectors at each timestep → (T, 3)
    rel = np.stack([
        df_a["rx_km"].to_numpy() - df_b["rx_km"].to_numpy(),
        df_a["ry_km"].to_numpy() - df_b["ry_km"].to_numpy(),
        df_a["rz_km"].to_numpy() - df_b["rz_km"].to_numpy(),
    ], axis=1)

    # Euclidean distance at each timestep
    d = np.linalg.norm(rel, axis=1)

    # Replace NaNs with +inf so they don’t affect the minimum
    d_safe = np.where(np.isfinite(d), d, np.inf)

    # Index of minimum safe distance
    return int(np.argmin(d_safe))


def _interp_component(t_s: np.ndarray, y: np.ndarray, t_new_s: np.ndarray) -> np.ndarray:
    """
    Interpolate a single state component (x, y, z, or velocity) onto a new time grid.

    - Uses linear interpolation (`np.interp`).
    - Handles NaNs by forward-filling and backward-filling edge values before interpolation.
    """
    if np.any(~np.isfinite(y)):
        mask = np.isfinite(y)
        if not mask.any():
            # All values are NaN → cannot interpolate
            return np.full_like(t_new_s, np.nan)
        # Forward fill NaNs
        for i in range(1, len(y)):
            if not np.isfinite(y[i]): 
                y[i] = y[i-1]
        # Backward fill NaNs
        for i in range(len(y)-2, -1, -1):
            if not np.isfinite(y[i]): 
                y[i] = y[i+1]
    return np.interp(t_new_s, t_s, y)


def _interp_state(df: pd.DataFrame, t_new: pd.DatetimeIndex) -> Tuple[np.ndarray, np.ndarray]:
    """
    Interpolate both position and velocity from a trajectory DataFrame onto a new time grid.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: time, rx_km, ry_km, rz_km, vx_kms, vy_kms, vz_kms.
    t_new : pd.DatetimeIndex
        Target refined time grid.

    Returns
    -------
    R : np.ndarray, shape (N,3)
        Interpolated positions in km.
    V : np.ndarray, shape (N,3)
        Interpolated velocities in km/s.
    """
    # Express times in seconds relative to t0 for numerical stability
    t0 = df["time"].iloc[0]
    t_s = (df["time"].view("int64") - t0.value) / 1e9   # coarse grid seconds
    t_new_s = (t_new.view("int64") - t0.value) / 1e9    # refined grid seconds

    # Interpolate positions
    rx = _interp_component(t_s, df["rx_km"].to_numpy().astype(float), t_new_s)
    ry = _interp_component(t_s, df["ry_km"].to_numpy().astype(float), t_new_s)
    rz = _interp_component(t_s, df["rz_km"].to_numpy().astype(float), t_new_s)

    # Interpolate velocities
    vx = _interp_component(t_s, df["vx_kms"].to_numpy().astype(float), t_new_s)
    vy = _interp_component(t_s, df["vy_kms"].to_numpy().astype(float), t_new_s)
    vz = _interp_component(t_s, df["vz_kms"].to_numpy().astype(float), t_new_s)

    # Stack into (N,3) arrays
    R = np.stack([rx, ry, rz], axis=1)
    V = np.stack([vx, vy, vz], axis=1)
    return R, V


def refine_pair(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    idx_hint: Optional[int] = None,
    window: int = 3,
    upsample: int = 10,
) -> Dict[str, object]:
    """
    Refine the Time of Closest Approach (TCA) between two satellites
    using interpolation inside a local time window.

    Parameters
    ----------
    df_a, df_b : pd.DataFrame
        Satellite trajectories on a common coarse grid.
    idx_hint : int, optional
        Index of coarse minimum distance (if known); otherwise computed.
    window : int
        Number of coarse steps on each side of idx_hint to include in refinement.
    upsample : int
        Factor by which to refine temporal resolution within the window.

    Returns
    -------
    dict
        {
          "tca_utc": ISO string of refined closest approach time,
          "dca_km": distance of closest approach [km],
          "vrel_kms": relative velocity magnitude at TCA [km/s],
          "idx_coarse": index of coarse-grid min,
          "idx_refined": index within refined grid where min occurs
        }
    """

    # Ensure both DataFrames share an identical time grid
    if not np.array_equal(df_a["time"].values, df_b["time"].values):
        raise ValueError("refine_pair requires identical time grids")

    times = df_a["time"]
    T = len(times)

    # If no coarse index provided, compute it from raw separation
    if idx_hint is None:
        idx_hint = _coarse_min_index(df_a, df_b)

    # Define window of coarse indices around hint
    i0 = max(0, idx_hint - window)
    i1 = min(T - 1, idx_hint + window)

    # If window collapses (too short time series), fall back to coarse result
    if i1 <= i0:
        tca = times[idx_hint]
        rel_v = np.array([
            df_a["vx_kms"].iloc[idx_hint] - df_b["vx_kms"].iloc[idx_hint],
            df_a["vy_kms"].iloc[idx_hint] - df_b["vy_kms"].iloc[idx_hint],
            df_a["vz_kms"].iloc[idx_hint] - df_b["vz_kms"].iloc[idx_hint],
        ])
        rel_r = np.array([
            df_a["rx_km"].iloc[idx_hint] - df_b["rx_km"].iloc[idx_hint],
            df_a["ry_km"].iloc[idx_hint] - df_b["ry_km"].iloc[idx_hint],
            df_a["rz_km"].iloc[idx_hint] - df_b["rz_km"].iloc[idx_hint],
        ])
        return {
            "tca_utc": tca.isoformat(),
            "dca_km": float(np.linalg.norm(rel_r)),
            "vrel_kms": float(np.linalg.norm(rel_v)),
            "idx_coarse": int(idx_hint),
            "idx_refined": int(idx_hint),
        }

    # Extract coarse window
    t_window = times[i0 : i1 + 1]

    # Refined time grid: subdivide intervals by `upsample` factor
    if upsample < 2:
        upsample = 2
    t_fine = pd.date_range(
        t_window[0], t_window[-1],
        periods=((len(t_window) - 1) * upsample + 1),
        tz="UTC"
    )

    # Interpolate both satellites to the refined grid
    Ra, Va = _interp_state(df_a, t_fine)
    Rb, Vb = _interp_state(df_b, t_fine)
    Rrel = Ra - Rb
    Vrel = Va - Vb

    # Refined distances
    d = np.linalg.norm(Rrel, axis=1)
    d_safe = np.where(np.isfinite(d), d, np.inf)
    j = int(np.argmin(d_safe))

    # Extract refined closest approach details
    tca = t_fine[j]
    dca = float(d_safe[j])
    vrel = float(np.linalg.norm(Vrel[j]))

    return {
        "tca_utc": tca.isoformat(),
        "dca_km": dca,
        "vrel_kms": vrel,
        "idx_coarse": int(idx_hint),
        "idx_refined": int(j),
    }


def refine_candidates(
    states: Dict[str, pd.DataFrame],
    candidates_df: pd.DataFrame,
    window: int = 3,
    upsample: int = 10,
) -> pd.DataFrame:
    """
    Apply refine_pair() to a batch of candidate conjunctions.

    Parameters
    ----------
    states : dict[str, pd.DataFrame]
        Dictionary mapping satellite name -> trajectory DataFrame.
    candidates_df : pd.DataFrame
        Must have columns: a, b, t_index (from coarse_screen).
    window : int
        Window size (coarse steps on each side) for interpolation.
    upsample : int
        Refinement factor for local time resolution.

    Returns
    -------
    pd.DataFrame
        Table of refined results with columns:
          - a, b : satellite names
          - t_index : coarse-grid index
          - t_idx_refined : refined-grid index
          - tca_utc : refined closest approach time (ISO string)
          - dca_km : distance of closest approach [km]
          - vrel_kms : relative velocity at TCA [km/s]
        Sorted by (dca_km, a, b).
    """
    rows = []
    for _, row in candidates_df.iterrows():
        a = row["a"]; b = row["b"]; idx = int(row["t_index"])
        # Refine this pair using local interpolation
        res = refine_pair(states[a], states[b], idx_hint=idx, window=window, upsample=upsample)
        rows.append({
            "a": a,
            "b": b,
            "t_index": idx,
            "t_idx_refined": res["idx_refined"],
            "tca_utc": res["tca_utc"],
            "dca_km": round(res["dca_km"], 6),
            "vrel_kms": round(res["vrel_kms"], 6),
        })
    return pd.DataFrame(rows).sort_values(["dca_km","a","b"]).reset_index(drop=True)

