from pathlib import Path
from typing import Dict
import json
import pandas as pd
from .plots import dist_time_plot, rel3d_html, save_distance_csv


def build_report(
    states: Dict[str, pd.DataFrame],
    refined_df: pd.DataFrame,
    outdir: Path,
    half_steps: int = 10,
) -> Path:
    """
    Assemble a human+machine readable report of refined conjunction candidates.

    Inputs
    ------
    states : dict[name -> DataFrame]
        Per-satellite trajectories (same structure used elsewhere in the pipeline).
    refined_df : DataFrame
        Output from refine_candidates(); expected columns:
        a, b, t_index, t_idx_refined, tca_utc, dca_km, vrel_kms.
    outdir : Path
        Destination directory for all report artifacts.
    half_steps : int
        Plotting window half-width (coarse steps before/after t_index) for figures.

    Outputs
    -------
    Path
        Path to the generated Markdown file (outdir / "report.md").
    Side effects
    ------------
    Writes:
      - figures/dist_{A}__{B}.png (distance vs time)
      - figures/rel3d_{A}__{B}.html (3D relative trajectory)
      - report.json (machine-readable summary)
      - report.md (human-readable summary with links)
    """

    # Normalize and create output directories (idempotent).
    outdir = Path(outdir)
    figdir = outdir / "figures"
    figdir.mkdir(parents=True, exist_ok=True)

    rows = []  # will hold per-pair report records

    # Iterate through refined candidate rows and render figures for each pair.
    for _, r in refined_df.iterrows():
        a = str(r["a"]); b = str(r["b"])
        idx = int(r["t_index"])  # coarse index to center plotting window

        # Produce 2D distance-vs-time PNG; focuses on local window around idx.
        png = dist_time_plot(
            states, a, b, idx_hint=idx, outdir=figdir, half_steps=half_steps
        )

        # Produce interactive 3D relative trajectory HTML for the same window.
        html = rel3d_html(
            states, a, b, idx_hint=idx, outdir=figdir, half_steps=half_steps
        )
        csv_path = save_distance_csv(states, a, b, idx_hint=idx, outdir=figdir, half_steps=half_steps)
    


        # Collect a machine-friendly record for JSON/Markdown.
        rows.append({
            "a": a,
            "b": b,
            "t_index": int(r["t_index"]),
            # t_idx_refined may be absent if only coarse results exist; default -1.
            "t_idx_refined": int(r.get("t_idx_refined", -1)),
            "tca_utc": str(r["tca_utc"]),
            "dca_km": float(r["dca_km"]),
            "vrel_kms": float(r["vrel_kms"]),
            # Store artifact paths relative to outdir so the report remains portable.
            "distance_plot": str(png.relative_to(outdir)),
            "rel3d_html": str(html.relative_to(outdir)),
            "distance_csv": str(csv_path.relative_to(outdir)),
            })

    # ---------- Write machine-readable summary ----------
    jpath = outdir / "report.json"
    with jpath.open("w") as f:
        json.dump({"pairs": rows}, f, indent=2)

    # ---------- Write human-readable Markdown ----------
    mpath = outdir / "report.md"
    with mpath.open("w") as f:
        f.write("# Conjunction Screening — Refined Results\n\n")

        if not rows:
            # No candidates → emit a minimal, explicit note.
            f.write("_No candidate pairs in the selected window._\n")
        else:
            # Markdown table header
            f.write("| A | B | TCA (UTC) | DCA (km) | Vrel (km/s) | Distance plot | 3D relative |\n")
            f.write("|---|---|-----------:|--------:|------------:|--------------|-------------|\n")

            # One row per pair with links to generated artifacts.
            for r in rows:
                f.write(
                    f"| {r['a']} | {r['b']} | {r['tca_utc']} | "
                    f"{r['dca_km']:.3f} | {r['vrel_kms']:.3f} | "
                    f"[PNG]({r['distance_plot']}) | [HTML]({r['rel3d_html']}) |\n"
                )

        # Clear disclaimer about modeling limitations to avoid misuse.
        f.write("\n\n_Disclaimer:_ TLE+SGP4, no covariance; figures are illustrative only.\n")

    # Return path to the Markdown report (primary human artifact).
    return mpath

