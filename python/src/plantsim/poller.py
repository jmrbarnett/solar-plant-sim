"""Poll every device concurrently once per interval and queue the readings."""
from __future__ import annotations

import asyncio
import logging
import random
from collections import Counter
from datetime import datetime, timedelta

from plantsim.clock import SimClock
from plantsim.devices import CommsError, Device, Reading

log = logging.getLogger(__name__)


class Poller:
    def __init__(self, devices: list[Device], clock: SimClock, interval_s: float,
                 queue: asyncio.Queue[Reading | None], timeout_s: float = 2.0,
                 latency_s: tuple[float, float] = (0.01, 0.05),
                 rng: random.Random | None = None) -> None:
        self.devices = devices
        self.clock = clock
        self.interval = timedelta(seconds=interval_s)
        self.queue = queue
        self.timeout_s = timeout_s
        self.latency_s = latency_s
        self._rng = rng or random.Random()
        self.missed: Counter[str] = Counter()   # failed polls per device
        self.cycles = 0

    async def _fetch(self, dev: Device, t: datetime) -> list[Reading]:
        """Stand-in for a network read. Module 3 replaces this with Modbus TCP."""
        await asyncio.sleep(self._rng.uniform(*self.latency_s))
        return dev.read(t)

    async def _poll_one(self, dev: Device, t: datetime) -> None:
        try:
            readings = await asyncio.wait_for(self._fetch(dev, t), self.timeout_s)
        except (CommsError, TimeoutError) as exc:
            self.missed[dev.code] += 1
            log.warning("poll %s @ %s failed: %s", dev.code, t, str(exc) or "timeout")
            return
        for r in readings:
            await self.queue.put(r)              # waits if the writer falls behind

    async def run(self, stop_at: datetime | None = None) -> None:
        loop = asyncio.get_running_loop()
        t = self.clock.now().replace(second=0, microsecond=0)
        while stop_at is None or t < stop_at:
            delay = self.clock.real_seconds_until(t)
            if delay > 0:
                await asyncio.sleep(delay)
            elif -delay > self.interval.total_seconds() / self.clock.scale:
                log.warning("poller is %.1f s behind schedule", -delay)
            started = loop.time()
            async with asyncio.TaskGroup() as tg:      # all polls run at once
                for dev in self.devices:
                    tg.create_task(self._poll_one(dev, t))
            self.cycles += 1
            log.debug("cycle %s: %d devices in %.3f s", t, len(self.devices), loop.time() - started)
            t += self.interval