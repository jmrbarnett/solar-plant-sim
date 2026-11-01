"""Async poller tests. With asyncio_mode = "auto", pytest runs these on an event loop."""
import asyncio
from datetime import datetime, timedelta

from fakes import FakeWeather, make_inverter
from plantsim.clock import SimClock
from plantsim.poller import Poller

START = datetime(2026, 10, 10, 17, 0)
FAST = 3600.0                                   # one simulated hour per real second


def drain(queue: asyncio.Queue) -> list:
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    return items


async def test_every_device_polled_each_cycle():
    devices = [make_inverter(FakeWeather(), code=f"SPS01_B01_INV0{i}") for i in (1, 2)]
    queue: asyncio.Queue = asyncio.Queue()
    poller = Poller(devices, SimClock(START, FAST), 60, queue, latency_s=(0, 0))
    await poller.run(stop_at=START + timedelta(minutes=3))
    readings = drain(queue)
    assert poller.cycles == 3
    assert len(readings) == 3 * 2 * 5            # cycles x devices x (4 points + COMM_ST)
    assert {r.ts for r in readings} == {START + timedelta(minutes=m) for m in range(3)}


async def test_dead_device_is_counted_and_others_still_polled():
    ok = make_inverter(FakeWeather(), code="SPS01_B01_INV01")
    dead = make_inverter(FakeWeather(), code="SPS01_B01_INV02",
                         comms_outage=(START, START + timedelta(hours=1)))
    queue: asyncio.Queue = asyncio.Queue()
    poller = Poller([ok, dead], SimClock(START, FAST), 60, queue, latency_s=(0, 0))
    await poller.run(stop_at=START + timedelta(minutes=3))
    assert poller.missed == {"SPS01_B01_INV02": 3}
    dead_rows = [r for r in drain(queue) if r.device == "SPS01_B01_INV02"]
    assert [(r.point, r.value) for r in dead_rows] == [("COMM_ST", 0.0)] * 3


async def test_slow_device_times_out():
    class SlowPoller(Poller):
        async def _fetch(self, dev, t):
            await asyncio.sleep(1.0)             # longer than the 0.05 s timeout
            return dev.read(t)

    queue: asyncio.Queue = asyncio.Queue()
    poller = SlowPoller([make_inverter(FakeWeather())], SimClock(START, FAST), 60, queue,
                        timeout_s=0.05)
    await poller.run(stop_at=START + timedelta(minutes=1))
    assert poller.missed["SPS01_B01_INV01"] == 1
    assert [(r.point, r.value) for r in drain(queue)] == [("COMM_ST", 0.0)]