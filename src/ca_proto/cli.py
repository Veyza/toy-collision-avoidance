# at top with other imports
import argparse
from argparse import ArgumentDefaultsHelpFormatter
from pathlib import Path

from . import get_version
from .config import Defaults
from .timeutil import parse_iso_utc
from .tle_io import load_tles, fetch_celestrak_group, save_text, sample_tles
from .propagate import propagate_group
from .screening import coarse_screen
from .refine import refine_candidates
from .reporting import build_report
from .dashboard import run_dashboard
from .dv_planner import plan_dv_for_refined


def _parse_window_or_die(start: str, end: str) -> None:
    """
    Validate start/end ISO strings and ensure end > start; exit with a friendly message if invalid.
    """
    try:
        t0 = parse_iso_utc(start)
        t1 = parse_iso_utc(end)
    except Exception as e:
        raise SystemExit(f"Invalid date format. Use ISO UTC like 2025-08-17T00:00:00Z. Details: {e}")
    if t1 <= t0:
        raise SystemExit("Invalid window: --end must be after --start.")




def cmd_propagate(args):
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    _ = parse_iso_utc(args.start); _ = parse_iso_utc(args.end)

    tles = load_tles(args.tles)
    if getattr(args, "sample", None):
        tles = sample_tles(tles, args.sample)

    states = propagate_group(tles, args.start, args.end, step_s=args.step)
    for name, df in states.items():
        safe = name.replace(" ", "_").replace("/", "_")
        df.to_csv(outdir / f"{safe}.csv", index=False)
    print(f"Wrote {len(states)} CSV file(s) to {outdir}")


def cmd_screen(args):
    tles = load_tles(args.tles)
    if getattr(args, "sample", None):
        tles = sample_tles(tles, args.sample)
    states = propagate_group(tles, args.start, args.end, step_s=args.step)
    df = coarse_screen(states, screen_km=args.screen_km)
    out_csv = Path(args.out)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"Wrote {len(df)} candidate pair(s) to {out_csv}")


def cmd_refine(args):
    import pandas as pd
    tles = load_tles(args.tles)
    if getattr(args, "sample", None):
        tles = sample_tles(tles, args.sample)
    states = propagate_group(tles, args.start, args.end, step_s=args.step)

    coarse = coarse_screen(states, screen_km=args.screen_km)
    if coarse.empty:
        cols = ["a","b","t_index","t_idx_refined","tca_utc","dca_km","vrel_kms"]
        out = pd.DataFrame(columns=cols)
    else:
        out = refine_candidates(states, coarse, window=args.window, upsample=args.upsample)

    out_csv = Path(args.out)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False)
    print(f"Wrote refined results for {len(out)} pair(s) to {out_csv}")


def cmd_report(args):
    import pandas as pd
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    _ = parse_iso_utc(args.start); _ = parse_iso_utc(args.end)

    tles = load_tles(args.tles)
    if getattr(args, "sample", None):
        tles = sample_tles(tles, args.sample)
    states = propagate_group(tles, args.start, args.end, step_s=args.step)
    coarse = coarse_screen(states, screen_km=args.screen_km)

    if coarse.empty:
        refined = pd.DataFrame(columns=["a","b","t_index","t_idx_refined","tca_utc","dca_km","vrel_kms"])
    else:
        refined = refine_candidates(states, coarse, window=args.window, upsample=args.upsample)

    # Save refined CSV
    refined_csv = outdir / "refined.csv"
    refined.to_csv(refined_csv, index=False)

    mpath = build_report(states, refined, outdir=outdir, half_steps=args.half_steps)
    print(f"Report written: {mpath}")

def cmd_fetch(args):
    txt = fetch_celestrak_group(args.group)
    save_text(txt, args.out)
    print(f"Saved {args.group} TLEs to {args.out}")


def cmd_dashboard(args):
    run_dashboard(args.artifacts, host=args.host, port=args.port)


def cmd_dvplan(args):
    import pandas as pd
    refined = pd.read_csv(args.refined)
    if refined.empty:
        raise SystemExit("No refined pairs found in CSV.")
    out = plan_dv_for_refined(
        refined, plan_time_iso=args.plan_time,
        target_dca_km=args.target_dca_km,
        max_dv_mps=args.max_dv_mps,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"Wrote {len(out)} DV suggestion(s) to {out_path}")


def main():
    examples = """Examples:
  # Propagate and write per-satellite CSV states
  ca_proto propagate --tles data/starlink.tle --start 2025-08-17T00:00:00Z --end 2025-08-17T01:00:00Z --out artifacts/prop

  # Coarse screen for pairs under 150 km and write candidates.csv
  ca_proto screen --tles data/starlink.tle --sample 120 --start 2025-08-17T00:00:00Z --end 2025-08-17T02:00:00Z --screen-km 150 --out artifacts/candidates.csv

  # Refine TCAs for those candidates
  ca_proto refine --tles data/starlink.tle --sample 120 --start 2025-08-17T00:00:00Z --end 2025-08-17T02:00:00Z --out artifacts/refined.csv

  # Full report + figures + html
  ca_proto report --tles data/starlink.tle --sample 120 --start 2025-08-17T00:00:00Z --end 2025-08-17T02:00:00Z --outdir artifacts/demo

  # Launch dashboard on an artifacts folder
  ca_proto dashboard --artifacts artifacts/demo
"""
    parser = argparse.ArgumentParser(
        prog="ca_proto",
        description="Collision Avoidance Prototype — TLE/SGP4 screening, refinement, plots & dashboard",
        epilog=examples,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", metavar="{propagate,screen,refine,report,fetch,dashboard}")

    parser.add_argument("--version", action="store_true", help="Show installed version and exit")

    # propagate
    p = sub.add_parser("propagate", help="Propagate TLEs and write per-satellite CSV states", formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument("--tles", required=True, help="Path to TLE file")
    p.add_argument("--start", required=True, help="Start time ISO (UTC), e.g., 2025-08-17T00:00:00Z")
    p.add_argument("--end", required=True, help="End time ISO (UTC)")
    p.add_argument("--step", type=float, default=Defaults.step_s, help="Step in seconds")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--sample", type=int, default=None, help="Randomly sample N satellites")
    p.set_defaults(func=cmd_propagate)

    # screen
    s = sub.add_parser("screen", help="Propagate & coarse-screen pairs by min grid distance", formatter_class=ArgumentDefaultsHelpFormatter)
    s.add_argument("--tles", required=True)
    s.add_argument("--start", required=True)
    s.add_argument("--end", required=True)
    s.add_argument("--step", type=float, default=Defaults.step_s)
    s.add_argument("--screen-km", type=float, default=10.0, help="Keep pairs with dmin < screen-km")
    s.add_argument("--out", required=True, help="Output CSV path for candidates")
    s.add_argument("--sample", type=int, default=None, help="Randomly sample N satellites")
    s.set_defaults(func=cmd_screen)

    # refine
    r = sub.add_parser("refine", help="Propagate, coarse-screen, then refine TCA locally", formatter_class=ArgumentDefaultsHelpFormatter)
    r.add_argument("--tles", required=True)
    r.add_argument("--start", required=True)
    r.add_argument("--end", required=True)
    r.add_argument("--step", type=float, default=Defaults.step_s)
    r.add_argument("--screen-km", type=float, default=10.0)
    r.add_argument("--window", type=int, default=3, help="Half-width (steps) around coarse min")
    r.add_argument("--upsample", type=int, default=10, help="Temporal upsample factor inside window")
    r.add_argument("--out", required=True, help="Output CSV path for refined results")
    r.add_argument("--sample", type=int, default=None, help="Randomly sample N satellites")
    r.set_defaults(func=cmd_refine)

    # report
    rep = sub.add_parser("report", help="Full pipeline: screen, refine, plots, markdown/json", formatter_class=ArgumentDefaultsHelpFormatter)
    rep.add_argument("--tles", required=True)
    rep.add_argument("--start", required=True)
    rep.add_argument("--end", required=True)
    rep.add_argument("--step", type=float, default=Defaults.step_s)
    rep.add_argument("--screen-km", type=float, default=10.0)
    rep.add_argument("--window", type=int, default=3)
    rep.add_argument("--upsample", type=int, default=10)
    rep.add_argument("--half-steps", type=int, default=10, help="Half window (steps) for distance plot & CSV window")
    rep.add_argument("--outdir", required=True, help="Output directory for artifacts")
    rep.add_argument("--sample", type=int, default=None, help="Randomly sample N satellites")
    rep.set_defaults(func=cmd_report)

    # fetch
    f = sub.add_parser("fetch", help="Download TLEs for a Celestrak GROUP into a file", formatter_class=ArgumentDefaultsHelpFormatter)
    f.add_argument("--group", required=True, help="Celestrak group (e.g., starlink, oneweb, active)")
    f.add_argument("--out", required=True, help="Path to write TLEs (e.g., data/starlink.tle)")
    f.set_defaults(func=cmd_fetch)

    # dashboard
    dashp = sub.add_parser("dashboard", help="Launch a local dashboard for an artifacts directory", formatter_class=ArgumentDefaultsHelpFormatter)
    dashp.add_argument("--artifacts", required=True, help="Path to artifacts directory (must contain refined.csv)")
    dashp.add_argument("--host", default="127.0.0.1")
    dashp.add_argument("--port", type=int, default=8050)
    dashp.set_defaults(func=cmd_dashboard)
    
    # Delta-v
    dv = sub.add_parser("dvplan", help="Generate Δv suggestions for refined results (toy along-track heuristic)")
    dv.add_argument("--refined", required=True, help="Path to refined.csv (from 'report' or 'refine')")
    dv.add_argument("--plan-time", required=True, help="Plan time ISO (UTC) to execute the burn, e.g., 2025-08-17T00:30:00Z")
    dv.add_argument("--target-dca-km", type=float, default=2.0, help="Desired along-track separation at TCA (km)")
    dv.add_argument("--max-dv-mps", type=float, default=0.05, help="Cap absolute Δv magnitude (m/s)")
    dv.add_argument("--out", required=True, help="Output CSV for suggestions")
    dv.set_defaults(func=cmd_dvplan)


    args = parser.parse_args()

    if args.version:
        print(f"ca_proto {get_version()}")
        return

    # If a subcommand needs times, validate them early for friendlier errors
    if getattr(args, "start", None) and getattr(args, "end", None):
        _parse_window_or_die(args.start, args.end)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()



if __name__ == "__main__":
    main()

