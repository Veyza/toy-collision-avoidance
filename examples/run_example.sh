#!/usr/bin/env bash
set -euo pipefail
python -m ca_proto --version
# In Hour 2+, this will run: python -m ca_proto detect --tles data/sample_tles.txt ...
