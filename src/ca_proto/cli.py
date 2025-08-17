import argparse

def main():
    parser = argparse.ArgumentParser(
        prog="ca_proto",
        description="Collision Avoidance Prototype — Hour 1 scaffold (CLI stub)"
    )
    sub = parser.add_subparsers(dest="cmd")

    # We'll implement `detect` in Hour 2–4; for now, provide a friendly stub.
    parser.add_argument("--version", action="store_true", help="Show version and exit")

    args = parser.parse_args()
    if args.version:
        print("ca_proto 0.0.1 (Hour 1)")
        return

    parser.print_help()

if __name__ == "__main__":
    main()
