import argparse
from pathlib import Path
from .tle_io import load_tles
from .propagate import propagate_group
from .timeutil import parse_iso_utc
from .config import Defaults
from .screening import coarse_screen

def main():
    parser = argparse.ArgumentParser(
        prog="ca_proto",
        description="Collision Avoidance Prototype — CLI"
    )
    sub = parser.add_subparsers(dest="cmd", required=False)
    s = sub.add_parser("screen", help="Propagate & coarse-screen pairs by min grid distance")
    s.add_argument("--tles", required=True, help="Path to TLE file")
    s.add_argument("--start", required=True, help="Start time ISO, e.g. 2025-08-16T00:00:00Z")
    s.add_argument("--end", required=True, help="End time ISO")
    s.add_argument("--step", type=float, default=Defaults.step_s, help="Step in seconds")
    s.add_argument("--screen-km", type=float, default=10.0, help="Keep pairs with dmin < screen-km")
    s.add_argument("--out", required=True, help="Output CSV path")
    s.set_defaults(func=cmd_screen)

    parser.add_argument("--version", action="store_true", help="Show version and exit")

    # NEW: propagate command for smoke test
    p = sub.add_parser("propagate", help="Propagate TLEs and write CSVs (Hour 2 smoke test)")
    p.add_argument("--tles", required=True, help="Path to TLE file")
    p.add_argument("--start", required=True, help="Start time ISO, e.g. 2025-08-16T00:00:00Z")
    p.add_argument("--end", required=True, help="End time ISO")
    p.add_argument("--step", type=float, default=Defaults.step_s, help="Step in seconds")
    p.add_argument("--out", required=True, help="Output directory (CSV files)")
    p.set_defaults(func=cmd_propagate)

    args = parser.parse_args()

    if args.version:
        print("ca_proto 0.0.1")
        return

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

def cmd_propagate(args):
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    # sanity parse
    _ = parse_iso_utc(args.start); _ = parse_iso_utc(args.end)

    tles = load_tles(args.tles)
    states = propagate_group(tles, args.start, args.end, step_s=args.step)
    for name, df in states.items():
        safe = name.replace(" ", "_").replace("/", "_")
        df.to_csv(outdir / f"{safe}.csv", index=False)
    print(f"Wrote {len(states)} CSV file(s) to {outdir}")

def cmd_screen(args):
    # propagate then screen; write single CSV
    tles = load_tles(args.tles)
    states = propagate_group(tles, args.start, args.end, step_s=args.step)
    df = coarse_screen(states, screen_km=args.screen_km)
    out_csv = Path(args.out)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"Wrote {len(df)} candidate pair(s) to {out_csv}")

if __name__ == "__main__":
    main()

