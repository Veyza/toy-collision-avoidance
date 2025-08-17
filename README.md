# Collision Avoidance Prototype

TLE-based conjunction screening and simple avoidance Δv suggestions (ops-style, rapid prototype).

**Disclaimer**

**TLEs + SGP4 are not suitable for operational maneuver decisions. This is a prototype.**

## Quickstart (will evolve)
```bash
pip install -r requirements.txt
python -m ca_proto --help

## Working with TLEs

This project does not commit orbital data files (TLEs) because they are large and change daily.  
Instead, you can fetch fresh TLEs directly from [Celestrak](https://celestrak.org):

```bash
# Example: fetch Starlink TLEs
python -m ca_proto fetch --group starlink --out data/starlink.tle

# Example: fetch OneWeb TLEs
python -m ca_proto fetch --group oneweb --out data/oneweb.tle

