#!/usr/bin/env bash
set -euo pipefail

python -m ca_proto fetch --group starlink --out data/starlink.tle

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

echo "✅ Done. Open artifacts/demo_run/report.md"
