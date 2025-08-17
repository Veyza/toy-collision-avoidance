from typing import Dict
import numpy as np
import pandas as pd
from sgp4.api import Satrec, jday
from .timeutil import time_grid

def _satrec_from_tle(line1: str, line2: str) -> Satrec:
    # Helper: create an sgp4.api.Satrec object from a pair of TLE lines.
    # Satrec is the propagator state object that can compute position/velocity from JDs.
    return Satrec.twoline2rv(line1, line2)

def propagate_group(df_tles: pd.DataFrame, start_iso: str, end_iso: str, step_s: float = 20.0) -> Dict[str, pd.DataFrame]:
    """
    For each row in df_tles (with columns: name, line1, line2), propagate the orbit
    over a regular time grid between start_iso and end_iso.

    Parameters
    ----------
    df_tles : pd.DataFrame
        Must have at least columns 'name', 'line1', 'line2'.
    start_iso, end_iso : str
        Start and end times as ISO 8601 strings (UTC).
    step_s : float
        Step size in seconds between consecutive propagation times (default = 20 s).

    Returns
    -------
    Dict[str, pd.DataFrame]
        Dictionary mapping object name -> trajectory DataFrame.
        Each DataFrame has columns:
          - time (pandas.DatetimeIndex, UTC)
          - rx_km, ry_km, rz_km : position in TEME frame [km]
          - vx_kms, vy_kms, vz_kms : velocity in TEME frame [km/s]
        DataFrame.attrs["had_errors"] is True if any propagation errors occurred.
    """

    # Build a regular time grid in UTC with step_s spacing
    times = time_grid(start_iso, end_iso, step_s)

    # Precompute Julian date (jd, fr) pairs for all times.
    # This avoids recomputing inside the loop for each satellite.
    jd = np.empty(len(times))
    fr = np.empty(len(times))
    for k, t in enumerate(times):
        # pandas.Timestamp 't' gives year, month, day, hour, etc.
        y, mo, d = t.year, t.month, t.day
        h, mi, s = t.hour, t.minute, t.second + t.microsecond * 1e-6
        # jday converts calendar date → (julian day, fraction of day)
        jd[k], fr[k] = jday(y, mo, d, h, mi, s)

    out: Dict[str, pd.DataFrame] = {}

    # Iterate over each TLE in the input DataFrame
    for _, row in df_tles.iterrows():
        name = str(row["name"])  # satellite name (stringified to be safe)
        sat = _satrec_from_tle(row["line1"], row["line2"])  # create SGP4 propagator

        r_list = []  # list of position vectors [x,y,z] in km
        v_list = []  # list of velocity vectors [vx,vy,vz] in km/s
        err_any = False  # flag if any errors occur during propagation

        # Propagate this satellite at each requested time
        for j in range(len(times)):
            e, r, v = sat.sgp4(jd[j], fr[j])  # propagate at JD
            if e != 0:
                # e != 0 indicates a propagation error (e.g., data out of validity)
                err_any = True
                # Append NaNs so output stays aligned with times
                r_list.append([np.nan, np.nan, np.nan])
                v_list.append([np.nan, np.nan, np.nan])
            else:
                # Valid result: append position (km) and velocity (km/s)
                r_list.append(r)
                v_list.append(v)

        # Convert results to numpy arrays for vectorized slicing
        arr_r = np.array(r_list, dtype=float)  # shape (N,3)
        arr_v = np.array(v_list, dtype=float)  # shape (N,3)

        # Build a trajectory DataFrame for this satellite
        df = pd.DataFrame({
            "time": times,
            "rx_km": arr_r[:, 0], "ry_km": arr_r[:, 1], "rz_km": arr_r[:, 2],
            "vx_kms": arr_v[:, 0], "vy_kms": arr_v[:, 1], "vz_kms": arr_v[:, 2],
        })

        # Attach metadata: True if any time step failed to propagate
        df.attrs["had_errors"] = err_any

        # Store in output dict under satellite name
        out[name] = df

    # Return dict of propagated trajectories
    return out

