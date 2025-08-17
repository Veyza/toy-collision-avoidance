from pathlib import Path
import pandas as pd

def load_tles(path_or_str: str) -> pd.DataFrame:
    """
    Load a txt file with consecutive 2-line TLEs with an optional name line above each pair.
    
    Returns a DataFrame with columns:
      - name (str): object name (or "UNKNOWN" if missing)
      - line1 (str): first line of the TLE
      - line2 (str): second line of the TLE
      - epoch (Timestamp, UTC): epoch of the element set (placeholder here, not yet extracted)
      - norad_id (int): NORAD catalog ID parsed from line1 (if possible)
    """

    # Ensure the file exists at the given path
    p = Path(path_or_str)
    if not p.exists():
        raise FileNotFoundError(f"TLE file not found: {p}")

    # Read file, strip trailing newlines, ignore blank lines
    lines = [ln.rstrip("\n") for ln in p.read_text().splitlines() if ln.strip()]
    recs = []  # will hold parsed TLE records
    i = 0

    # Iterate over the lines and group them into name+TLE or just TLE
    while i < len(lines):
        # Case 1: current line looks like "line1" (starts with '1 ') and next line is "line2" (starts with '2 ')
        if lines[i].startswith("1 ") and (i + 1) < len(lines) and lines[i+1].startswith("2 "):
            name = "UNKNOWN"      # no name line provided, use default
            line1 = lines[i]      # line 1 of TLE
            line2 = lines[i+1]    # line 2 of TLE
            i += 2                # advance by 2 lines
        else:
            # Case 2: assume current line is a satellite name, followed by line1 + line2
            name = lines[i]
            if (i + 2) >= len(lines):  # not enough lines left for a full TLE
                break
            line1 = lines[i+1]
            line2 = lines[i+2]
            i += 3                    # advance by 3 lines (name + 2 TLE lines)

        # Validate that the lines look like a proper TLE pair
        if not (line1.startswith("1 ") and line2.startswith("2 ")):
            # Skip malformed block
            continue

        # Extract NORAD ID (satellite catalog number).
        # TLE format: first token of line1 is "1 XXXXXU ..." where XXXXX is the catalog number.
        try:
            norad = int(line1.split()[1][0:5])
        except Exception:
            norad = None  # leave blank if parsing fails

        # Append parsed record (epoch extraction is left for later with SGP4 parsing)
        recs.append({
            "name": name,
            "line1": line1,
            "line2": line2,
            "norad_id": norad
        })

    # Convert list of records into a pandas DataFrame
    df = pd.DataFrame.from_records(recs)

    # Guard against empty result (e.g., file malformed or only blanks)
    if df.empty:
        raise ValueError("No valid TLEs parsed")

    return df
    
    
import requests
from datetime import datetime

CELESTRAK_TLE_URL = "https://celestrak.org/NORAD/elements/gp.php"

def fetch_celestrak_group(group: str) -> str:
    """
    Download a 2-line TLE text for a Celestrak GROUP (e.g., 'starlink','oneweb','active').
    Returns the raw text. Caller should save to disk.
    """
    params = {"GROUP": group, "FORMAT": "tle"}
    r = requests.get(CELESTRAK_TLE_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.text

def save_text(text: str, out_path: str) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(text)

def sample_tles(df, n: int, seed: int = 42):
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=seed).reset_index(drop=True)


