from typing import Dict, Tuple, List
import numpy as np
import pandas as pd

def _extract_positions(states: Dict[str, pd.DataFrame]) -> Tuple[List[str], np.ndarray, pd.DatetimeIndex]:
    """
    Convert dict{name -> df} (trajectory states) into a compact numpy array form.

    Parameters
    ----------
    states : Dict[str, pd.DataFrame]
        Dictionary mapping satellite name -> trajectory DataFrame.
        Each DataFrame must have columns:
          - "time" (pandas.DatetimeIndex, UTC, identical across all satellites)
          - "rx_km", "ry_km", "rz_km" (position in km, TEME frame).

    Returns
    -------
    names : list[str]
        List of satellite names, in the same order as in the array.
    R : np.ndarray
        Shape (N, T, 3). Positions in km for N satellites over T time steps.
        Axis 0 = satellite, axis 1 = time index, axis 2 = coordinates (x,y,z).
    times : pd.DatetimeIndex
        Common time grid (length T, UTC).
    """

    names = list(states.keys())
    if not names:
        raise ValueError("no states given")

    # Use the time grid of the *first* satellite as the reference.
    # Assumes all satellites share the same time grid (validated below).
    t0 = states[names[0]]["time"]
    T = len(t0)

    # Allocate 3D array for positions: (satellite, timestep, xyz)
    R = np.empty((len(names), T, 3), dtype=float)

    for i, name in enumerate(names):
        df = states[name]

        # Sanity check: ensure required column exists
        if "time" not in df.columns:
            raise ValueError(f"{name} missing 'time' column")

        # Check that time grid matches reference exactly (length + values)
        if len(df) != T or not np.all(df["time"].values == t0.values):
            raise ValueError("time grids differ between satellites; cannot screen coarsely")

        # Extract x, y, z positions into the big array
        R[i, :, 0] = df["rx_km"].to_numpy()
        R[i, :, 1] = df["ry_km"].to_numpy()
        R[i, :, 2] = df["rz_km"].to_numpy()

    # Return names, stacked position array, and common time grid
    return names, R, pd.DatetimeIndex(t0)


def pairwise_min_distance(names: List[str], R: np.ndarray) -> List[Tuple[str, str, float, int]]:
    """
    Compute coarse minimum distances between every pair of satellites on the given grid.

    Parameters
    ----------
    names : list[str]
        Satellite names, length N.
    R : np.ndarray
        Positions, shape (N, T, 3) with N satellites and T timesteps.

    Returns
    -------
    list[tuple]
        For each unordered pair (i, j), returns a tuple:
          (name_i, name_j, dmin_km, idx_min)
        where:
          - dmin_km : minimum separation distance found [km]
          - idx_min : index of the timestep where the minimum occurred
    """

    N, T, _ = R.shape
    out = []

    # Loop over all unique unordered pairs of satellites
    for i in range(N):
        for j in range(i + 1, N):

            # Compute relative position vector time series: shape (T, 3)
            rel = R[i] - R[j]

            # Euclidean distance at each timestep: shape (T,)
            d = np.linalg.norm(rel, axis=1)

            # Handle NaNs from failed propagations:
            # - If *all* values are NaN, skip this pair entirely
            if np.all(~np.isfinite(d)):
                continue

            # Replace NaNs with +inf so they never appear as minima
            d_safe = np.where(np.isfinite(d), d, np.inf)

            # Find the time index of minimum separation
            idx = int(np.argmin(d_safe))
            dmin = float(d_safe[idx])

            # Skip pairs where the "minimum" is still infinite (all invalid)
            if np.isinf(dmin):
                continue

            # Append result tuple for this pair
            out.append((names[i], names[j], dmin, idx))

    return out

