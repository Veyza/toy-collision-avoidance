# Artifacts Directory

This folder holds generated artifacts from running the pipeline
(screening → refine → report → dashboard).

Typical contents:
- `refined.csv` — table of refined conjunctions
- `figures/` — per-pair plots:
  - `dist_<a>__<b>.csv` — distance vs time data
  - `dist_<a>__<b>.png` — distance plot
  - `rel3d_<a>__<b>.html` — 3D relative trajectory
- `dv_suggestions.csv` — optional Δv sandbox outputs

## Demo run

Artifacts are **not versioned** in git.  
To generate a minimal demo dataset locally:

```bash
python -m ca_proto fetch --group starlink --out data/starlink.tle

python -m ca_proto report \
  --tles data/starlink.tle --sample 120 \
  --start 2025-08-17T00:00:00Z --end 2025-08-17T02:00:00Z \
  --step 30 --screen-km 150 --window 3 --upsample 20 \
  --half-steps 10 --dv-target-km 2.0 --dv-max-mps 0.05 \
  --outdir artifacts/starlink_demo
Then open the dashboard:

bash
Copy
Edit
python -m ca_proto dashboard --artifacts artifacts/starlink_demo
