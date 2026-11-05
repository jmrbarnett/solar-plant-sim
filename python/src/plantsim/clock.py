"""Accelerated simulation clock: maps real elapsed time to simulated time."""
import time
from datetime import datetime, timedelta


class SimClock:
    def __init__(self, start: datetime, scale: float) -> None:
        self.start = start
        self.scale = scale                  # simulated seconds per real second
        self._t0 = time.monotonic()         # never jumps, unlike the wall clock

    def now(self) -> datetime:
        return self.start + timedelta(seconds=(time.monotonic() - self._t0) * self.scale)

    def real_seconds_until(self, t: datetime) -> float:
        return (t - self.now()).total_seconds() / self.scale