import argparse
from pathlib import Path

from .config import Defaults
from .timeutil import parse_iso_utc
from .tle_io import (
    load_tles,
    fetch_celestrak_group,
    save_text,
    sample_tles,   # ← this must be present
)
from .propagate import propagate_group
from .screening import coarse_screen
from .refine import refine_candidates
from .reporting import build_report


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


def main():
    parser = argparse.ArgumentParser(
        prog="ca_proto",
        description="Collision Avoidance Prototype — CLI"
    )
    sub = parser.add_subparsers(dest="cmd", required=False)

    parser.add_argument("--version", action="store_true", help="Show version and exit")

    # propagate
    p = sub.add_parser("propagate", help="Propagate TLEs and write CSVs")
    p.add_argument("--sample", type=int, default=None, help="Randomly sample N satellites from the TLE file")
    p.add_argument("--tles", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--step", type=float, default=Defaults.step_s)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_propagate)

    # screen
    s = sub.add_parser("screen", help="Propagate & coarse-screen")
    s.add_argument("--tles", required=True)
    s.add_argument("--start", required=True)
    s.add_argument("--sample", type=int, default=None, help="Randomly sample N satellites from the TLE file")
    s.add_argument("--end", required=True)
    s.add_argument("--step", type=float, default=Defaults.step_s)
    s.add_argument("--screen-km", type=float, default=10.0)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_screen)

    # refine
    r = sub.add_parser("refine", help="Propagate, coarse-screen, then refine")
    r.add_argument("--tles", required=True)
    r.add_argument("--start", required=True)
    r.add_argument("--sample", type=int, default=None, help="Randomly sample N satellites from the TLE file")
    r.add_argument("--end", required=True)
    r.add_argument("--step", type=float, default=Defaults.step_s)
    r.add_argument("--screen-km", type=float, default=10.0)
    r.add_argument("--window", type=int, default=3)
    r.add_argument("--upsample", type=int, default=10)
    r.add_argument("--out", required=True)
    r.set_defaults(func=cmd_refine)

    # report
    rep = sub.add_parser("report", help="Propagate, screen, refine, and build a report with plots")
    rep.add_argument("--tles", required=True)
    rep.add_argument("--start", required=True)
    rep.add_argument("--end", required=True)
    rep.add_argument("--sample", type=int, default=None, help="Randomly sample N satellites from the TLE file")
    rep.add_argument("--step", type=float, default=Defaults.step_s)
    rep.add_argument("--screen-km", type=float, default=10.0)
    rep.add_argument("--window", type=int, default=3)
    rep.add_argument("--upsample", type=int, default=10)
    rep.add_argument("--half-steps", type=int, default=10)
    rep.add_argument("--outdir", required=True)
    rep.set_defaults(func=cmd_report)
    
    # fetch
    f = sub.add_parser("fetch", help="Download TLEs for a Celestrak GROUP into a file")
    f.add_argument("--group", required=True, help="Celestrak group name (e.g., starlink, oneweb, iridium, active)")
    f.add_argument("--out", required=True, help="Path to write TLEs (e.g., data/starlink.tle)")
    f.add_argument("--sample", type=int, default=None, help="Randomly sample N satellites from the TLE file")
    f.set_defaults(func=cmd_fetch)


    args = parser.parse_args()

    if args.version:
        print("ca_proto 0.0.1 (Hour 5)")
        return

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

