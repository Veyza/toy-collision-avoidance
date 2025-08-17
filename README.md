# Collision Avoidance Prototype

**Disclaimer**  
This project is a **prototype** for research and demonstration only.  
**TLEs + SGP4 are not suitable for operational maneuver decisions.**  
Do not use this software for real collision avoidance planning.

---

## Overview

This package implements a rapid prototype for **TLE-based conjunction screening**  
and **toy Δv suggestions** (ops-style heuristics).

Main features:
1. **Fetch** Two-Line Element (TLE) sets from Celestrak.  
2. **Screen** for close approaches (conjunction candidates).  
3. **Refine** trajectories around the Time of Closest Approach (TCA).  
4. **Report** results in CSV/Markdown/JSON.  
5. **Visualize** outcomes in static plots and interactive dashboards.  
6. **Sandbox** simple Δv avoidance heuristics.

---

## Installation

Clone the repository and install in editable mode:
```bash
git clone https://github.com/<your-org>/toy-collision-avoidance.git
cd toy-collision-avoidance
pip install -e .
```
For development:
```bash
pip install -r requirements.txt
```

## Version
To check the installed version:
```bash
python -m pip show ca-proto
```
## Usage
Get general help:
```bash
python -m ca_proto --help
```
Main subcommands:

fetch — download TLEs from Celestrak

report — run screening/refinement pipeline and generate artifacts

dashboard — open interactive results dashboard

## Example: Starlink Demo Run
1. Fetch TLEs
(we don’t commit TLE data files to git)
```bash
python -m ca_proto fetch --group starlink --out data/starlink.tle
```
2. Run analysis
```bash
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
```
This writes outputs into artifacts/demo_run/:

refined.csv — refined close approaches (TCA, DCA, relative velocity)

report.md & report.json — human-readable + machine-readable summaries

figures/*.png — distance vs time plots

figures/*.html — interactive 3D relative trajectories

Sample outputs are included in the examples/ folder.
(The included CSVs/PNGs are shortened examples; real runs generate more files.)

3. Open the dashboard
```bash
python -m ca_proto dashboard --artifacts artifacts/demo_run
```
Then open http://127.0.0.1:8050/ in your browser.

## Artifacts
Generated outputs are written into the artifacts/ directory.
The folder contains a README.md and .gitkeep to ensure the directory exists in git.
