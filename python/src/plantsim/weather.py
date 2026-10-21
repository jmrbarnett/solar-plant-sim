"""Site weather: plane-of-array irradiance, ambient and module temperature."""
from __future__ import annotations

import math
import random
from datetime import datetime
from typing import Protocol

NOCT_RISE_C_PER_WM2 = 25.0 / 800.0   # module runs ~25 C above ambient at 800 W/m2


class WeatherSource(Protocol):
    """Anything with these methods can drive the devices (real Weather or a test fake)."""
    def poa_wm2(self, t: datetime) -> float: ...
    def ambient_c(self, t: datetime) -> float: ...
    def module_temp_c(self, t: datetime) -> float: ...


class Weather:
    def __init__(self, rng: random.Random, sunrise_utc: float = 11.3, sunset_utc: float = 23.0) -> None:
        self._rng = rng
        self.sunrise_utc = sunrise_utc
        self.sunset_utc = sunset_utc
        self._cloud = 1.0
        self._minute: datetime | None = None

    @staticmethod
    def _hour(t: datetime) -> float:
        return t.hour + t.minute / 60 + t.second / 3600

    def _update_cloud(self, t: datetime) -> None:
        """Random-walk the cloud factor once per simulated minute."""
        minute = t.replace(second=0, microsecond=0)
        if minute != self._minute:
            self._cloud = min(1.0, max(0.3, self._cloud + self._rng.gauss(0, 0.03)))
            self._minute = minute

    def poa_wm2(self, t: datetime) -> float:
        self._update_cloud(t)
        h = self._hour(t)
        if not self.sunrise_utc < h < self.sunset_utc:
            return 0.0
        x = (h - self.sunrise_utc) / (self.sunset_utc - self.sunrise_utc)
        return 1000.0 * math.sin(math.pi * x) ** 1.2 * self._cloud

    def ambient_c(self, t: datetime) -> float:
        return 22.0 + 8.0 * max(0.0, math.sin(math.pi * (self._hour(t) - 11) / 14))

    def module_temp_c(self, t: datetime) -> float:
        return self.ambient_c(t) + self.poa_wm2(t) * NOCT_RISE_C_PER_WM2