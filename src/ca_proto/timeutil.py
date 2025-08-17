from datetime import datetime, timezone
import pandas as pd

def parse_iso_utc(s: str) -> datetime:
    # Parse an ISO 8601 timestamp string into a Python datetime with UTC timezone.
    # Examples of accepted formats: "2025-08-16T12:00:00Z" or "2025-08-16T12:00:00+00:00".
    
    # Use pandas to handle flexible ISO datetime parsing and force UTC.
    dt = pd.to_datetime(s, utc=True)
    
    # Convert pandas.Timestamp to a standard Python datetime,
    # and ensure tzinfo is explicitly set to UTC.
    return dt.to_pydatetime().replace(tzinfo=timezone.utc)

def time_grid(start_iso: str, end_iso: str, step_s: float):
    # Generate a sequence of times between two ISO 8601 timestamps
    # at a fixed step size (in seconds).

    # Parse input ISO strings into timezone-aware Python datetimes (UTC).
    t0 = parse_iso_utc(start_iso)
    t1 = parse_iso_utc(end_iso)

    # Validate that the end time is strictly after the start time.
    if t1 <= t0:
        raise ValueError("end must be after start")

    # Create a pandas DatetimeIndex with evenly spaced times
    # from t0 to t1 (inclusive), with frequency = step_s seconds,
    # all in UTC timezone.
    return pd.date_range(
        t0, t1,
        freq=f"{int(step_s)}S",  # step as whole seconds
        inclusive="both",        # include both start and end in the range
        tz="UTC"                 # ensure UTC timezone
    )

