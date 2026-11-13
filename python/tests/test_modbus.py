"""Field server + Modbus poller over a real TCP connection on localhost (Module 3)."""
import asyncio
from datetime import datetime, timedelta

import pytest

from fakes import FakeWeather, make_inverter
from plantsim.clock import SimClock
from plantsim.devices import MetStation
from plantsim.field import FieldServer
from plantsim.modbus_poller import ModbusPoller

START = datetime(2026, 10, 10, 17, 0)
FAST = 3600.0                                   # one simulated hour per real second
PORT = 15020                                    # not 5020, so a running plantsim can't clash


def drain(queue: asyncio.Queue) -> list:
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    return items


async def poll_once(devices, latency_s=(0, 0)):
    clock = SimClock(START, FAST)
    field = FieldServer(devices, clock, port=PORT, latency_s=latency_s)
    await field.start()
    queue: asyncio.Queue = asyncio.Queue()
    poller = ModbusPoller(devices, clock, 60, queue, port=PORT, request_timeout_s=0.2)
    try:
        await poller.run(stop_at=START + timedelta(minutes=1))
    finally:
        poller.close()
        await field.stop()
    return poller, drain(queue)


async def test_values_arrive_over_modbus():
    inv = make_inverter(FakeWeather())
    met = MetStation("SPS01_MET01", FakeWeather(poa=812.34, ambient=-3.0))
    poller, readings = await poll_once([inv, met])
    got = {(r.device, r.point): r.value for r in readings}
    expected = inv.state(START)
    assert got[("SPS01_B01_INV01", "AC_P_KW")] == pytest.approx(expected["AC_P_KW"], abs=0.001)
    assert got[("SPS01_B01_INV01", "CAB_TEMP_C")] == pytest.approx(expected["CAB_TEMP_C"], abs=0.05)
    assert got[("SPS01_MET01", "POA_IRR_WM2")] == pytest.approx(812.3)
    assert got[("SPS01_MET01", "AMB_TEMP_C")] == pytest.approx(-3.0)       # negative survives
    assert got[("SPS01_MET01", "COMM_ST")] == 1.0
    assert poller.missed == {}


async def test_comms_outage_is_a_modbus_exception():
    dead = make_inverter(FakeWeather(), comms_outage=(START, START + timedelta(hours=1)))
    poller, readings = await poll_once([dead])
    assert poller.missed == {"SPS01_B01_INV01": 1}
    assert [(r.point, r.value) for r in readings] == [("COMM_ST", 0.0)]


async def test_slow_device_times_out():
    poller, readings = await poll_once([make_inverter(FakeWeather())], latency_s=(0.5, 0.5))
    assert poller.missed == {"SPS01_B01_INV01": 1}
    assert [(r.point, r.value) for r in readings] == [("COMM_ST", 0.0)]
