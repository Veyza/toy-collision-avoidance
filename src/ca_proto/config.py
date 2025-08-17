from dataclasses import dataclass

@dataclass(frozen=True)
class Defaults:
    step_s: float = 20.0  # default step
    # screening thresholds etc. will go here later

