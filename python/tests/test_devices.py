"""Unit tests for device physics and comms behaviour."""
from datetime import datetime, timedelta

import pytest

from fakes import FakeWeather, make_inverter
from plantsim.devices import CommsError, Meter, MetStation, OperState

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
    