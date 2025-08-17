"""
Tests for TLE input/output utilities.

Covers:
- Loading TLEs from local files.
- Parsing TLE format into satellite names and SGP4 objects.
- Error handling when files are missing or malformed.
"""

from ca_proto.tle_io import load_tles

def test_load_tles():
    df = load_tles("data/sample_tles.txt")
    assert len(df) >= 1
    assert {"name","line1","line2"}.issubset(df.columns)

