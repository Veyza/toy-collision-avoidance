"""
Smoke tests for the command-line interface.

Covers:
- Top-level commands (--help, --version).
- Subcommand availability and usage messages.
- Argument validation (e.g. required inputs, time window order).
"""

import sys
import subprocess
from pathlib import Path

PY = sys.executable

def run_cli(args, cwd: Path = Path(".")):
    """Run `python -m ca_proto <args>` and return (code, stdout, stderr)."""
    proc = subprocess.run(
        [PY, "-m", "ca_proto", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_cli_version():
    code, out, err = run_cli(["--version"])
    assert code == 0
    # Accept either stdout or stderr depending on platform quirks
    combined = out + err
    assert "ca_proto" in combined
    # has a semantic version-ish number
    assert any(ch.isdigit() for ch in combined)


def test_cli_help_top_level():
    code, out, err = run_cli(["--help"])
    assert code == 0
    combined = out + err
    # Should mention subcommands and a short description we set
    assert "propagate" in combined
    assert "screen" in combined
    assert "refine" in combined
    assert "report" in combined
    assert "fetch" in combined
    assert "dashboard" in combined
    assert "Collision Avoidance Prototype" in combined


def test_report_requires_args():
    # Missing required args should yield non-zero and show usage
    code, out, err = run_cli(["report"])
    assert code != 0
    combined = out + err
    assert "usage:" in combined.lower()
    assert "--tles" in combined


def test_time_window_validation():
    # end before start should fail with our friendly message
    code, out, err = run_cli([
        "screen",
        "--tles", "data/does_not_matter.tle",
        "--start", "2025-01-02T00:00:00Z",
        "--end",   "2025-01-01T00:00:00Z",
        "--out", "artifacts/tmp.csv",
    ])
    assert code != 0
    combined = out + err
    assert "must be after" in combined.lower() or "invalid window" in combined.lower()

