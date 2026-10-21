"""Simulated field devices. Each reports named points for a simulated time."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

from plantsim.weather import WeatherSource

TEMP_COEFF_PER_C = -0.0035   # panel power change per degree C above 25 C
INVERTER_EFF = 0.975
METER_LOSS_FACTOR = 0.985    # transformer and cable losses to the POI


class Quality(IntEnum):      # OPC-style quality codes, as in the telemetry table
    BAD = 0
    UNCERTAIN = 64
    GOOD = 192


class OperState(IntEnum):
    OFF = 1                  # night / no DC input
    RUNNING = 2
    FAULT = 3


@dataclass(frozen=True)
class Reading:
    device: str
    point: str
    ts: datetime
    value: float
    quality: Quality = Quality.GOOD


class CommsError(Exception):
    """The device did not respond (simulated communication loss)."""


class Device(ABC):
    def __init__(self, code: str, comms_outage: tuple[datetime, datetime] | None = None) -> None:
        self.code = code
        self._outage = comms_outage
        self._state_t: datetime | None = None
        self._state: dict[str, float] = {}

    def state(self, t: datetime) -> dict[str, float]:
        """Physical state at time t, computed once per t and cached."""
        if t != self._state_t:
            self._state, self._state_t = self._compute(t), t
        return self._state

    def read(self, t: datetime) -> list[Reading]:
        """What a SCADA poll returns. Fails during a comms outage."""
        if self._outage and self._outage[0] <= t < self._outage[1]:
            raise CommsError(f"{self.code}: no response")
        return [Reading(self.code, name, t, round(value, 3))
                for name, value in self.state(t).items()]

    @abstractmethod
    def _compute(self, t: datetime) -> dict[str, float]: ...


class Inverter(Device):
    def __init__(self, code: str, weather: WeatherSource, dc_kw: float, rated_kw: float,
                 derate: float = 1.0, rng: random.Random | None = None,
                 comms_outage: tuple[datetime, datetime] | None = None) -> None:
        super().__init__(code, comms_outage)
        self.weather = weather
        self.dc_kw = dc_kw
        self.rated_kw = rated_kw
        self.derate = derate               # < 1.0 simulates a DC-side fault
        self._rng = rng or random.Random()

    def _compute(self, t: datetime) -> dict[str, float]:
        g = self.weather.poa_wm2(t)
        amb = self.weather.ambient_c(t)
        if g <= 0:
            return {"AC_P_KW": 0.0, "DC_P_KW": 0.0, "CAB_TEMP_C": amb,
                    "OPER_ST": float(OperState.OFF)}
        temp_factor = 1 + TEMP_COEFF_PER_C * (self.weather.module_temp_c(t) - 25)
        dc = (self.dc_kw * g / 1000 * temp_factor * self.derate
              * self._rng.uniform(0.98, 1.0))          # small string-to-string scatter
        ac = min(self.rated_kw, dc * INVERTER_EFF)     # clipping
        return {"AC_P_KW": ac, "DC_P_KW": dc,
                "CAB_TEMP_C": amb + 25 * ac / self.rated_kw,
                "OPER_ST": float(OperState.RUNNING)}


class Meter(Device):
    """Revenue meter at the POI: sums inverter output, even from inverters that are
    not communicating. Comms loss is a data problem, not an energy problem."""
    def __init__(self, code: str, inverters: list[Inverter],
                 comms_outage: tuple[datetime, datetime] | None = None) -> None:
        super().__init__(code, comms_outage)
        self.inverters = inverters

    def _compute(self, t: datetime) -> dict[str, float]:
        total = sum(inv.state(t)["AC_P_KW"] for inv in self.inverters)
        return {"AC_P_KW": total * METER_LOSS_FACTOR}


class MetStation(Device):
    def __init__(self, code: str, weather: WeatherSource,
                 comms_outage: tuple[datetime, datetime] | None = None) -> None:
        super().__init__(code, comms_outage)
        self.weather = weather

    def _compute(self, t: datetime) -> dict[str, float]:
        return {"POA_IRR_WM2": self.weather.poa_wm2(t),
                "AMB_TEMP_C": self.weather.ambient_c(t),
                "MOD_TEMP_C": self.weather.module_temp_c(t)}