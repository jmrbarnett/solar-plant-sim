"""Tests for the Weather model (Exercise 2.3a)."""
import random
from datetime import datetime, timedelta

from plantsim.weather import Weather

DAY = datetime(2026, 10, 10)


def every_minute(start: datetime, end: datetime):
    t = start
    while t < end:
        yield t
        t += timedelta(minutes=1)


def test_dark_at_night_and_light_at_noon():
    w = Weather(random.Random(1))
    assert w.poa_wm2(DAY.replace(hour=3)) == 0.0       # 03:00 UTC = 11 p.m. EDT (it's dark)
    assert w.poa_wm2(DAY.replace(hour=17)) > 0.0       # 17:00 UTC = 1 p.m. EDT, near solar noon


def test_never_negative_over_a_day():
    w = Weather(random.Random(1))
    assert all(w.poa_wm2(t) >= 0.0 for t in every_minute(DAY, DAY + timedelta(days=1)))


def test_cloud_factor_stays_between_limits_over_a_day():
    w = Weather(random.Random(1))
    for t in every_minute(DAY, DAY + timedelta(days=1)):
        w.poa_wm2(t)                                   # advances the cloud random walk
        assert 0.3 <= w._cloud <= 1.0, f"cloud factor {w._cloud} out of range at {t}"