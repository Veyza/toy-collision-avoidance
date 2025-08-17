# Collision Avoidance Prototype

TLE-based conjunction screening and simple avoidance Δv suggestions (ops-style, rapid prototype).

**Disclaimer**

**TLEs + SGP4 are not suitable for operational maneuver decisions. This is a prototype.**

## Quickstart (will evolve)
```bash
pip install -r requirements.txt
python -m ca_proto --help


## Working with TLEs

## Demo run (Starlink sample)

Fetch current TLEs (we don’t commit TLE data files):
```bash
python -m ca_proto fetch --group starlink --out data/starlink.tle


Run a sample end-to-end report:

python -m ca_proto report \
  --tles data/starlink.tle \
  --sample 120 \
  --start 2025-08-17T00:00:00Z \
  --end   2025-08-17T02:00:00Z \
  --step  30 \
  --screen-km 150 \
  --window 3 \
  --upsample 20 \
  --half-steps 10 \
  --outdir artifacts/demo_run
  
Or run the script:
```bash
examples/run_demo.sh
  
Outputs (written to artifacts/demo_run/):

refined.csv — refined close approaches with tca_utc, dca_km, vrel_kms
report.md & report.json — human + machine summaries
figures/*.png — distance vs time around TCA (PNG)
figures/*.html — interactive 3D relative trajectory (HTML)

Sample output from a real run in "examples".
