"""Build the plant from config, then run poller and writer together."""
from __future__ import annotations

import argparse
import asyncio
import logging
import random
from datetime import timedelta
from pathlib import Path

from plantsim.clock import SimClock
from plantsim.config import Config, load
from plantsim.db import PointRegistry, connect
from plantsim.devices import Device, Inverter, Meter, MetStation, Reading
from plantsim.poller import Poller
from plantsim.weather import Weather
from plantsim.writer import TelemetryWriter

log = logging.getLogger("plantsim")


def build_plant(cfg: Config) -> list[Device]:
    rng = random.Random(cfg.sim.seed)
    weather = Weather(random.Random(rng.random()))
    site, faults = cfg.site, cfg.faults
    n_inverters = site.blocks * site.inverters_per_block
    outage = None
    if faults.comms_start:
        outage = (faults.comms_start, faults.comms_start + timedelta(minutes=faults.comms_minutes))

    inverters = []
    for b in range(1, site.blocks + 1):
        for i in range(1, site.inverters_per_block + 1):
            code = f"{site.code}_B{b:02d}_INV{i:02d}"
            inverters.append(Inverter(
                code, weather,
                dc_kw=site.dc_kw / n_inverters,
                rated_kw=site.inverter_rated_kw,
                derate=faults.underperformer_derate if code == faults.underperformer else 1.0,
                rng=random.Random(rng.random()),
                comms_outage=outage if code == faults.comms_device else None,
            ))
    meter = Meter(f"{site.code}_MTR01", inverters)
    met = MetStation(f"{site.code}_MET01", weather)
    return [*inverters, meter, met]


async def main(config_path: Path, hours: float) -> None:
    cfg = load(config_path)
    clock = SimClock(cfg.sim.start, cfg.sim.time_scale)
    queue: asyncio.Queue[Reading | None] = asyncio.Queue(maxsize=10_000)
    poller = Poller(build_plant(cfg), clock, cfg.sim.poll_interval_s, queue)
    writer = TelemetryWriter(connect, PointRegistry(cfg.site.code))
    stop_at = cfg.sim.start + timedelta(hours=hours)
    log.info("simulating %s from %s to %s at %gx", cfg.site.code, cfg.sim.start, stop_at,
             cfg.sim.time_scale)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(writer.run(queue))
        await poller.run(stop_at)
        await queue.put(None)                 # tell the writer we're done

    log.info("done: %d cycles, %d rows written, %d dropped, missed polls %s",
             poller.cycles, writer.rows_written, writer.rows_dropped, dict(poller.missed))


def run() -> None:
    parser = argparse.ArgumentParser(description="Solar plant telemetry simulator")
    parser.add_argument("--config", type=Path, default=Path("config/plant.toml"))
    parser.add_argument("--hours", type=float, default=12.0, help="simulated hours to run")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    try:
        asyncio.run(main(args.config, args.hours))
    except KeyboardInterrupt:
        log.info("stopped by user")