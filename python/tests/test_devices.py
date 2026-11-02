"""Unit tests for device physics and comms behaviour."""
import random
from datetime import datetime, timedelta

import pytest

from fakes import FakeWeather, make_inverter
from plantsim.devices import CommsError, Meter, MetStation, OperState, Tracker, TrackerMode

T = datetime(2026, 10, 10, 17, 0)


@pytest.mark.parametrize("poa", [850.0, 1000.0, 1100.0])
def test_inverter_clips_at_rating(poa):
    s = make_inverter(FakeWeather(poa=poa)).state(T)
    assert s["AC_P_KW"] == 250.0
    assert s["DC_P_KW"] * 0.975 > 250.0          # more DC than the inverter can pass


def test_derate_fully_visible_below_clipping():
    healthy = make_inverter(FakeWeather(poa=500.0), seed=7).state(T)["AC_P_KW"]
    faulty = make_inverter(FakeWeather(poa=500.0), derate=0.75, seed=7).state(T)["AC_P_KW"]
    assert faulty / healthy == pytest.approx(0.75)


def test_hot_modules_lose_power():
    cool = make_inverter(FakeWeather(poa=500.0, module=25.0)).state(T)["DC_P_KW"]
    hot = make_inverter(FakeWeather(poa=500.0, module=45.0)).state(T)["DC_P_KW"]
    assert hot / cool == pytest.approx(1 - 0.0035 * 20)    # 7% loss at +20 C


def test_night_is_off():
    s = make_inverter(FakeWeather(poa=0.0)).state(T)
    assert s["AC_P_KW"] == 0.0
    assert s["OPER_ST"] == OperState.OFF


def test_state_is_cached_per_timestamp():
    inv = make_inverter(FakeWeather(poa=500.0))
    first = inv.state(T)
    assert inv.state(T) is first                              # no second random draw
    assert inv.state(T + timedelta(minutes=1)) is not first


def test_comms_outage_blocks_reads_only_inside_window():
    inv = make_inverter(FakeWeather(), comms_outage=(T, T + timedelta(minutes=20)))
    with pytest.raises(CommsError):
        inv.read(T + timedelta(minutes=5))
    assert inv.read(T + timedelta(minutes=20))               # half-open: end is excluded


def test_meter_counts_inverter_during_comms_outage():
    inv = make_inverter(FakeWeather(poa=500.0), comms_outage=(T, T + timedelta(minutes=20)))
    (reading,) = Meter("SPS01_MTR01", [inv]).read(T)
    assert reading.value == pytest.approx(inv.state(T)["AC_P_KW"] * 0.985, abs=0.001)


def test_met_station_points():
    names = {r.point for r in MetStation("SPS01_MET01", FakeWeather()).read(T)}
    assert names == {"POA_IRR_WM2", "AMB_TEMP_C", "MOD_TEMP_C"}


# --- Trackers (Exercise 2.5) ---

def make_tracker(stuck_from=None, seed=1) -> Tracker:
    return Tracker("SPS01_B01_TRK03", FakeWeather(), stuck_from=stuck_from,
                   rng=random.Random(seed))


@pytest.mark.parametrize("hour, expected", [
    (3.0, 0.0),          # night: before sunrise, flat
    (11.29, 0.0),        # just before sunrise
    (11.31, -60.0),      # just after sunrise
    (12.0, -60.0),       # morning: clamped at the east limit
    (15.0, -32.25),      # tilted east, following the sun
    (17.15, 0.0),        # solar noon: flat
    (20.0, 42.75),       # tilted west
    (22.5, 60.0),        # evening: clamped at the west limit
    (22.99, 60.0),       # just before sunset
    (23.01, 0.0),        # just after sunset
    (23.5, 0.0),         # night after sunset, flat
])
def test_tracker_target_follows_the_sun(hour, expected):
    t = datetime(2026, 10, 10) + timedelta(hours=hour)
    assert make_tracker().target_deg(t) == pytest.approx(expected, abs=0.01)


def test_healthy_tracker_stays_close_to_target():
    trk = make_tracker()
    for minute in range(0, 12 * 60):                 # 11:00 to 23:00
        t = datetime(2026, 10, 10, 11) + timedelta(minutes=minute)
        s = trk.state(t)
        assert abs(s["ANG_ACT_DEG"] - s["ANG_TGT_DEG"]) <= 0.3


def test_stuck_tracker_holds_zero_from_fault_time():
    fault = datetime(2026, 10, 10, 18, 0)
    trk = make_tracker(stuck_from=fault)
    before = trk.state(fault - timedelta(minutes=1))
    after = trk.state(fault + timedelta(hours=2))    # 20:00, target is +42.75
    assert before["ANG_ACT_DEG"] == pytest.approx(before["ANG_TGT_DEG"], abs=0.3)
    assert after["ANG_ACT_DEG"] == 0.0
    assert after["ANG_TGT_DEG"] > 40.0               # the gap SQL will look for
    assert after["MODE_ST"] == float(TrackerMode.TRACKING)   # controller doesn't notice


def test_tracker_points():
    names = {r.point for r in make_tracker().read(T)}
    assert names == {"ANG_TGT_DEG", "ANG_ACT_DEG", "MODE_ST"}
    