from typing import Dict, List, Tuple
import pandas as pd
from .geometry import _extract_positions, pairwise_min_distance

def coarse_screen(states: Dict[str, pd.DataFrame], screen_km: float) -> pd.DataFrame:
    """
    Coarse screening of satellite conjunctions.

    For each satellite pair:
      - compute the minimum distance over the propagated time grid
      - keep only pairs with min distance < screen_km

    Parameters
    ----------
    states : dict[str, pd.DataFrame]
        Dictionary mapping satellite name -> trajectory DataFrame,
        each with 'time', 'rx_km', 'ry_km', 'rz_km' columns.
    screen_km : float
        Screening threshold distance in kilometers.

    Returns
    -------
    pd.DataFrame
        A table of possible close approaches with columns:
          - a : name of satellite A
          - b : name of satellite B
          - dmin_km : minimum separation distance [km]
          - t_index : integer index of timestep where min occurred
          - time_utc : ISO string of UTC time at that index
        Sorted by (dmin_km, a, b). Empty DataFrame if no pairs found.
    """

    # Convert input dictionary of DataFrames into
    # (names, positions array, time grid)
    names, R, times = _extract_positions(states)

    # Compute minimum distance for every unordered pair of satellites
    tuples: List[Tuple[str, str, float, int]] = pairwise_min_distance(names, R)
    cols = ["a", "b", "dmin_km", "t_index", "time_utc"]
    
    # If no valid pairs were found, return an empty DataFrame with the right columns
    if not tuples:
        return pd.DataFrame(columns=["a", "b", "dmin_km", "t_index", "time_utc"])

    rows = []
    # Filter pairs by screening threshold
    for a, b, dmin, idx in tuples:
        if dmin < screen_km:
            rows.append({
                "a": a,                       # satellite A name
                "b": b,                       # satellite B name
                "dmin_km": round(dmin, 6),    # minimum distance (rounded for readability)
                "t_index": int(idx),          # index of timestep in the time grid
                "time_utc": times[idx].isoformat()  # ISO UTC string of that timestep
            })
    # If no pairs pass the screen_km threshold, returns an empty DataFrame with the expected columns. 
    if not rows:
        return pd.DataFrame(columns=cols)
    # Build final DataFrame, sort by distance then by names, reset row indices
    df = pd.DataFrame(rows).sort_values(["dmin_km", "a", "b"]).reset_index(drop=True)
    return df

