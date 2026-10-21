"""Test doubles shared by the test modules."""
import random

from plantsim.devices import Inverter


class FakeWeather:
    """Fixed conditions so results are predictable. Satisfies the WeatherSource protocol."""
    def __init__(self, poa: float = 1000.0, ambient: float = 25.0, module: float = 25.0) -> None:
        self.poa, self.ambient, self.module = poa, ambient, module

    def poa_wm2(self, t): return self.poa
    def ambient_c(self, t): return self.ambient
    def module_temp_c(self, t): return self.module


def make_inverter(weather, code="SPS01_B01_INV01", derate=1.0, seed=1, **kwargs) -> Inverter:
    """A 325 kW-DC / 250 kW-AC inverter, like the simulator's (DC/AC ratio 1.3)."""
    return Inverter(code, weather, dc_kw=325.0, rated_kw=250.0, derate=derate,
                    rng=random.Random(seed), **kwargs)