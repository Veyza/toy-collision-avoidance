from pathlib import Path
import pandas as pd
from ca_proto.reporting import build_report

def test_build_report_empty(tmp_path: Path):
    states = {}  # not used when refined is empty
    refined = pd.DataFrame(columns=["a","b","t_index","t_idx_refined","tca_utc","dca_km","vrel_kms"])
    mpath = build_report(states, refined, outdir=tmp_path)
    assert mpath.exists()
    assert (tmp_path / "report.json").exists()

