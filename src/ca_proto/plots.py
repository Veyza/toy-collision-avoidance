from pathlib import Path
from typing import Dict, Tuple
import numpy as np
import pandas as pd
import plotly.graph_objects as go

def _safe_name(x: str) -> str:
    """
    Utility: sanitize satellite name into a safe filename component
    by replacing spaces and slashes with underscores.
    """
    return str(x).replace(" ", "_").replace("/", "_")


def _distance_series(df_a: pd.DataFrame, df_b: pd.DataFrame) -> pd.Series:
    """
    Compute pairwise distance time series between two satellites.

    Parameters
    ----------
    df_a, df_b : pd.DataFrame
        Trajectories on a shared time grid (with rx_km, ry_km, rz_km columns).

    Returns
    -------
    pd.Series
        Separation distances [km] with datetime index (UTC).
    """
    # Relative position vectors (T,3)
    rel = np.stack([
        df_a["rx_km"].to_numpy() - df_b["rx_km"].to_numpy(),
        df_a["ry_km"].to_numpy() - df_b["ry_km"].to_numpy(),
        df_a["rz_km"].to_numpy() - df_b["rz_km"].to_numpy(),
    ], axis=1)

    # Norm gives distance at each timestep
    d = np.linalg.norm(rel, axis=1)

    # Return as pandas Series with same time index
    return pd.Series(d, index=df_a["time"])


def _window_slice(df_a: pd.DataFrame, df_b: pd.DataFrame, center_idx: int, half_steps: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract a local time window of two trajectories around a candidate close approach.

    Parameters
    ----------
    df_a, df_b : pd.DataFrame
        Trajectories on a common time grid.
    center_idx : int
        Index of coarse-grid closest approach (hint).
    half_steps : int
        Number of steps before/after the index to include.

    Returns
    -------
    (df_a_window, df_b_window) : Tuple[pd.DataFrame, pd.DataFrame]
        Subset DataFrames restricted to the window [i0, i1].
    """
    i0 = max(0, center_idx - half_steps)
    i1 = min(len(df_a) - 1, center_idx + half_steps)
    return df_a.iloc[i0:i1+1], df_b.iloc[i0:i1+1]


def dist_time_plot(states: Dict[str, pd.DataFrame], a: str, b: str, idx_hint: int, outdir: Path, half_steps: int = 10) -> Path:
    """
    Plot and save a 2D distance-vs-time plot for a satellite pair.

    Parameters
    ----------
    states : dict[str, pd.DataFrame]
        Dict mapping name -> trajectory DataFrame.
    a, b : str
        Names of satellites to compare.
    idx_hint : int
        Index of candidate closest approach (center of window).
    outdir : Path
        Output directory for saving the PNG.
    half_steps : int
        Number of coarse timesteps before/after hint to include in the plot.

    Returns
    -------
    Path
        Path to saved PNG file (requires `kaleido` for Plotly image export).
    """
    outdir.mkdir(parents=True, exist_ok=True)

    # Restrict to local window around hint
    df_a = states[a]; df_b = states[b]
    dfw_a, dfw_b = _window_slice(df_a, df_b, idx_hint, half_steps)

    # Compute distance series for this window
    s = _distance_series(dfw_a, dfw_b)

    # Create interactive figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name="Distance (km)"))

    # Highlight the coarse minimum distance in the window
    j = int(np.nanargmin(s.values))
    t_min = s.index[j]
    d_min = float(s.values[j])
    fig.add_trace(go.Scatter(x=[t_min], y=[d_min], mode="markers", name="Grid min"))

    # Style axes and layout
    fig.update_layout(
        title=f"Separation vs Time — {a} vs {b}",
        xaxis_title="Time (UTC)",
        yaxis_title="Separation (km)",
        margin=dict(l=50, r=20, t=60, b=50),
    )

    # Save to PNG file
    fname = outdir / f"dist_{_safe_name(a)}__{_safe_name(b)}.png"
    fig.write_image(str(fname))  # Requires 'kaleido' backend for Plotly
    return fname


def rel3d_html(states: Dict[str, pd.DataFrame], a: str, b: str, idx_hint: int, outdir: Path, half_steps: int = 10) -> Path:
    """
    Plot and save a 3D relative trajectory visualization for a satellite pair.

    Parameters
    ----------
    states : dict[str, pd.DataFrame]
        Dict mapping name -> trajectory DataFrame.
    a, b : str
        Names of satellites to compare.
    idx_hint : int
        Index of candidate closest approach (center of window).
    outdir : Path
        Output directory for saving the HTML.
    half_steps : int
        Number of coarse timesteps before/after hint to include in the plot.

    Returns
    -------
    Path
        Path to saved HTML file (interactive Plotly visualization).
    """
    outdir.mkdir(parents=True, exist_ok=True)

    # Restrict to local window around hint
    df_a = states[a]; df_b = states[b]
    dfw_a, dfw_b = _window_slice(df_a, df_b, idx_hint, half_steps)

    # Compute relative position time series (satellite A relative to B)
    rx = dfw_a["rx_km"].to_numpy() - dfw_b["rx_km"].to_numpy()
    ry = dfw_a["ry_km"].to_numpy() - dfw_b["ry_km"].to_numpy()
    rz = dfw_a["rz_km"].to_numpy() - dfw_b["rz_km"].to_numpy()

    # 3D line plot of relative trajectory in TEME frame
    fig = go.Figure(data=[go.Scatter3d(x=rx, y=ry, z=rz, mode="lines", name="Rel traj")])
    fig.update_layout(
        title=f"Relative trajectory (ECI/TEME) — {a} vs {b}",
        scene=dict(xaxis_title="x (km)", yaxis_title="y (km)", zaxis_title="z (km)"),
        margin=dict(l=20, r=20, t=60, b=20),
    )

    # Save to interactive HTML file (self-contained with CDN JS)
    fname = outdir / f"rel3d_{_safe_name(a)}__{_safe_name(b)}.html"
    fig.write_html(str(fname), include_plotlyjs="cdn")
    return fname

