from pathlib import Path
from typing import Dict
import json
import pandas as pd
import plotly.graph_objects as go

# ✅ import dash primitives
from dash import Dash, dcc, html, Input, Output, State
from dash import dash_table  # NEW (you can use later for the pairs table)
import dash

import numpy as np  # NEW (used in minor checks)

from .dv_planner import plan_dv_for_refined  # NEW


def _pairs_from_refined(refined_csv: Path):
    """
    Load refined results CSV and build dropdown options.

    Parameters
    ----------
    refined_csv : Path
        Path to CSV with refined results (must contain columns a, b, tca_utc).

    Returns
    -------
    (df, options)
        df : DataFrame of refined results
        options : list of dicts for Dash dropdown, each with:
            - label: human-readable (e.g., "SatA vs SatB @ 2025-08-16T12:00Z")
            - value: machine token "A||B"
            - tca: TCA time string
    """
    df = pd.read_csv(refined_csv)
    if df.empty:
        return df, []
    # Build readable labels combining satellite names and TCA time
    df["label"] = df.apply(
        lambda r: f"{str(r['a']).strip()} vs {str(r['b']).strip()} @ {str(r['tca_utc'])}",
        axis=1
    )
    return df, [
        {"label": lab, "value": f"{r['a']}||{r['b']}", "tca": r["tca_utc"]}
        for lab, r in zip(df["label"], df.to_dict("records"))
    ]


def _distance_csv_path(artifacts_dir: Path, a: str, b: str):
    """
    Build the path to a pair’s distance-vs-time CSV (saved earlier as artifact).
    Filenames sanitize spaces/slashes.
    """
    safe = lambda x: str(x).replace(" ", "_").replace("/", "_")
    return artifacts_dir / "figures" / f"dist_{safe(a)}__{safe(b)}.csv"


def _rel3d_html_path(artifacts_dir: Path, a: str, b: str):
    """
    Build the path to a pair’s 3D relative trajectory HTML artifact.
    """
    safe = lambda x: str(x).replace(" ", "_").replace("/", "_")
    return artifacts_dir / "figures" / f"rel3d_{safe(a)}__{safe(b)}.html"


def run_dashboard(artifacts_dir: str, host: str = "127.0.0.1", port: int = 8050):
    """
    Launch a local Dash web app to browse refined conjunction results.

    Inputs
    ------
    artifacts_dir : str
        Directory containing artifacts (refined.csv, figures/, etc.).
    host : str
        Host interface to bind the server (default: localhost).
    port : int
        Port for the dashboard (default: 8050).
    """
    artifacts = Path(artifacts_dir)
    refined_csv = artifacts / "refined.csv"

    # Load refined candidates and pre-build dropdown options
    refined_df, options = _pairs_from_refined(refined_csv)

    # Initialize Dash app
    app = Dash(__name__)
    app.title = "CA Prototype Dashboard"

    # ---------- Layout ----------
    app.layout = html.Div([
        html.H2("Collision Avoidance Prototype — Results Browser"),

        # Dropdown selector for candidate pair
        html.Div([
            html.Label("Pair:"),
            dcc.Dropdown(
                id="pair-dropdown",
                options=options,
                value=(options[0]["value"] if options else None),
                style={"width": "600px"}
            ),
        ], style={"marginBottom": "12px"}),

        # Metrics panel (TCA, DCA, vrel)
        html.Div(id="metrics", style={"marginBottom": "16px", "fontSize": "16px"}),

        # --- Δv sandbox controls (toy heuristic) ---
        html.H4("Δv sandbox (toy heuristic)"),
        html.Div([
            html.Label("Plan time (UTC)"),
            dcc.Input(id="dv-plan-time", type="text", value="", placeholder="e.g. 2025-08-17T00:30:00Z"),
            html.Label("Target DCA (km)", style={"marginLeft":"16px"}),
            dcc.Input(id="dv-target-km", type="number", value=2.0, step=0.1),
            html.Label("Max |Δv| (m/s)", style={"marginLeft":"16px"}),
            dcc.Input(id="dv-max-mps", type="number", value=0.05, step=0.01),
            html.Button("Compute", id="dv-run", n_clicks=0, style={"marginLeft":"16px"}),
        ], style={"display":"flex","alignItems":"center","gap":"8px","marginBottom":"10px"}),

        # Where DV suggestions will render (cards)
        html.Div(id="dv-results", style={"display":"flex","gap":"10px","flexWrap":"wrap","marginBottom":"16px"}),

        # Distance vs time figure
        dcc.Graph(id="dist-graph"),

        html.Div([
            html.B("Note: "),
            html.Span(
                "The red dot marks the refined TCA (time of closest approach). "
                "It uses the refined timing but is placed by interpolation on the coarse distance curve. "
                "Therefore it does not necessarily coincide with the apparent minimum of the blue line, "
                "which is sampled at discrete coarse steps."
            )
        ], style={"fontSize": "15px", "color": "#444", "marginBottom": "20px"}),

        # Embedded 3D HTML
        html.H4("3D Relative Trajectory"),
        html.Iframe(
            id="rel3d-frame",
            # Use srcDoc to embed HTML content directly (avoid file:// blocking)
            srcDoc="",
            style={"width": "100%", "height": "500px", "border": "1px solid #ccc"}
        ),
        html.Div([
            html.B("Note: "),
            html.Span(
                "This 3D plot shows the relative trajectory of satellite A with respect to B in the TEME (True Equator, Mean Equinox) frame. "
                "It is not Earth-fixed, so the orientation does not match ground geography but illustrates the relative motion."
            )
        ], style={"fontSize": "15px", "color": "#444", "marginBottom": "24px"}),

        # Hidden store: holds absolute artifacts dir path for callbacks
        dcc.Store(id="artifacts-dir", data=str(artifacts.resolve())),
    ], style={"maxWidth": "1100px", "margin": "24px auto"})

    # ---------- Callbacks ----------

    @app.callback(
        Output("metrics", "children"),
        Output("dist-graph", "figure"),
        Output("rel3d-frame", "srcDoc"),  # embed HTML via srcDoc instead of src
        Input("pair-dropdown", "value"),
        State("artifacts-dir", "data"),
        State("dv-target-km", "value"),   # for target line overlay
        prevent_initial_call=False,        # run once on load
    )
    def update_outputs(pair_value, artifacts_root, target_dca_km):
        """
        Update metrics panel, distance-vs-time plot, and 3D iframe when
        user selects a satellite pair from dropdown.
        """
        if not pair_value:
            return "No pairs available.", go.Figure(), ""

        # Split token "A||B" into names
        a, b = pair_value.split("||", 1)

        # Retrieve matching refined row (order-insensitive)
        row = refined_df[
            ((refined_df["a"] == a) & (refined_df["b"] == b)) |
            ((refined_df["a"] == b) & (refined_df["b"] == a))
        ]

        # Default metrics
        metrics = "No data"
        if not row.empty:
            r = row.iloc[0]
            # Build metrics panel with pair info, TCA, DCA, vrel
            metrics = html.Div([
                html.Div(f"Pair: {str(r['a']).strip()} vs {str(r['b']).strip()}"),
                html.Div(f"TCA (UTC): {r['tca_utc']}"),
                html.Div(f"DCA (km): {float(r['dca_km']):.3f}    |    Vrel (km/s): {float(r['vrel_kms']):.3f}")
            ])

        # Build distance-vs-time figure from CSV artifact (if exists)
        dist_csv = _distance_csv_path(Path(artifacts_root), a, b)
        fig = go.Figure()
        if dist_csv.exists():
            df = pd.read_csv(dist_csv)
            # main line
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(df["time_utc"]),
                y=df["distance_km"],
                mode="lines",
                name="Distance (km)",
                line=dict(width=3)
            ))

            # add a CA marker using refined time; compute y by interpolating on the plotted series
            if not row.empty:
                r = row.iloc[0]
                t_min = pd.to_datetime(r["tca_utc"])

                # Interpolate the distance at the refined time on the plotted series
                ts = pd.to_datetime(df["time_utc"])
                ys = df["distance_km"].to_numpy()

                # Convert times to int64 ns for robust interpolation
                t_ns = ts.astype("int64").to_numpy()
                t_ref_ns = t_min.value

                # Clamp to range to avoid NaN if refined time is slightly outside the window
                t_ref_ns = max(int(t_ns.min()), min(int(t_ns.max()), int(t_ref_ns)))

                # Linear interpolation (matches the straight-line segments Plotly draws)
                y_ref = float(np.interp(t_ref_ns, t_ns, ys))

                fig.add_trace(go.Scatter(
                    x=[pd.to_datetime(t_ref_ns)],
                    y=[y_ref],
                    mode="markers",
                    name=f"Grid min<br>{t_min.strftime('%Y-%m-%d %H:%M:%S')}"
                ))

            fig.update_layout(
                title=f"Separation vs Time — {str(a).strip()} vs {str(b).strip()}",
                xaxis_title="Time (UTC)",
                yaxis_title="Separation (km)",
                font=dict(size=14),
                legend=dict(font=dict(size=12)),
                showlegend=True,  # force legend visible
                margin=dict(l=60, r=20, t=60, b=60),
            )
            fig.update_xaxes(tickfont=dict(size=12), title_font=dict(size=14), title_standoff=25)
            fig.update_yaxes(tickfont=dict(size=12), title_font=dict(size=14), title_standoff=30)

            # Optional target DCA overlay line (if user provided a number)
            try:
                if target_dca_km is not None and float(target_dca_km) > 0:
                    fig.add_hline(
                        y=float(target_dca_km),
                        line_dash="dot",
                        annotation_text="Target DCA",
                        annotation_position="top right"
                    )
            except Exception:
                pass

        # Link 3D iframe to HTML artifact by embedding file content (srcDoc)
        rel_html = _rel3d_html_path(Path(artifacts_root), a, b)
        rel_srcdoc = ""
        if rel_html.exists():
            try:
                rel_srcdoc = rel_html.read_text(encoding="utf-8")
            except Exception:
                rel_srcdoc = "<p>Could not read 3D HTML file.</p>"

        return metrics, fig, rel_srcdoc

    # --- DV sandbox: helper to render a card ---
    def _dv_card(row: dict) -> html.Div:
        """Render one small card for a DV suggestion row."""
        direction = "prograde" if float(row["suggested_dv_mps"]) > 0 else "retrograde"
        return html.Div([
            html.B(f"Actor {str(row['actor']).upper()} — {direction}"),
            html.Div(f"Δv: {float(row['suggested_dv_mps']):.3f} m/s"),
            html.Div(f"Δt: {float(row['dt_to_tca_s']):.1f} s"),
            html.Div(f"Achieved DCA: {float(row['achieved_dca_km']):.3f} km"),
        ], style={"border":"1px solid #ddd","padding":"10px","borderRadius":"10px","width":"260px"})

    @app.callback(
        Output("dv-results", "children"),
        Input("dv-run", "n_clicks"),
        State("pair-dropdown", "value"),
        State("dv-plan-time", "value"),
        State("dv-target-km", "value"),
        State("dv-max-mps", "value"),
        prevent_initial_call=True,
    )
    def run_dv_sandbox(n_clicks, pair_value, plan_time, target_km, max_dv):
        """
        Compute Δv suggestions for the currently selected pair using the toy heuristic.
        - If plan_time is empty, default to 'now' in UTC.
        """
        if not n_clicks or not pair_value:
            return []

        # Build a one-row refined_df for the selected pair
        a, b = pair_value.split("||", 1)
        try:
            r = refined_df[
                ((refined_df["a"] == a) & (refined_df["b"] == b)) |
                ((refined_df["a"] == b) & (refined_df["b"] == a))
            ].iloc[0]
        except Exception:
            return [html.Div("No refined row for the selected pair.", style={"color":"#a00"})]

        # Default plan time: now (UTC) if not provided
        if not plan_time or not str(plan_time).strip():
            plan_time = pd.Timestamp.utcnow().replace(microsecond=0).isoformat() + "Z"

        # Defaults / coercions
        try:
            target_km = float(target_km) if target_km is not None else 2.0
            max_dv = float(max_dv) if max_dv is not None else 0.05
        except Exception:
            return [html.Div("Invalid DV parameters (target/max).", style={"color":"#a00"})]

        # Build a tiny refined_df for the planner
        refined_one = pd.DataFrame([{
            "a": str(r["a"]),
            "b": str(r["b"]),
            "tca_utc": str(r["tca_utc"]),
            "dca_km": float(r["dca_km"]),
            "vrel_kms": float(r["vrel_kms"]),
            "t_index": int(r.get("t_index", 0)),
            "t_idx_refined": int(r.get("t_idx_refined", -1)),
        }])

        # Run the existing planner
        dv_df = plan_dv_for_refined(
            refined_df=refined_one,
            plan_time_iso=str(plan_time),
            target_dca_km=target_km,
            max_dv_mps=max_dv,
        )

        if dv_df.empty:
            return [html.Div("Plan time is after TCA — no suggestions.", style={"color":"#a00"})]

        # Render cards: actor A and B, both directions
        cards = []
        for _, row in dv_df.iterrows():
            cards.append(_dv_card(row))

        # Add a small disclaimer under the cards
        cards.append(html.Div(
            "Note: Δs≈Δv·Δt; toy along-track heuristic only (no covariance / orbital element control).",
            style={"fontSize":"13px", "color":"#555", "marginTop":"6px"}
        ))
        return cards

    # ---------- Run server ----------
    # Dash >= 3 uses app.run; older versions use app.run_server
    try:
        run = getattr(app, "run", None) or getattr(app, "run_server")
        run(host=host, port=port, debug=False)
    except AttributeError:
        # Very old versions fallback
        app.run_server(host=host, port=port, debug=False)

