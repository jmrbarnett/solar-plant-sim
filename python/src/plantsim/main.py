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
from plantsim.devices import Device, Inverter, Meter, MetStation, Reading, Tracker

from plantsim.field import FieldServer
from plantsim.modbus_poller import ModbusPoller
from plantsim.registers import unit_ids

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

    trackers = []                                  # one per inverter, same block and number
    for b in range(1, site.blocks + 1):
        for i in range(1, site.inverters_per_block + 1):
            code = f"{site.code}_B{b:02d}_TRK{i:02d}"
            trackers.append(Tracker(
                code, weather,
                stuck_from=faults.stuck_tracker_from if code == faults.stuck_tracker else None,
                rng=random.Random(rng.random()),
            ))

    meter = Meter(f"{site.code}_MTR01", inverters)
    met = MetStation(f"{site.code}_MET01", weather)
    return [*inverters, *trackers, meter, met]


async def main(config_path: Path, hours: float) -> None:
    cfg = load(config_path)
    clock = SimClock(cfg.sim.start, cfg.sim.time_scale)
    devices = build_plant(cfg)
    field = FieldServer(devices, clock, cfg.modbus.host, cfg.modbus.port)
    queue: asyncio.Queue[Reading | None] = asyncio.Queue(maxsize=10_000)
    poller = ModbusPoller(devices, clock, cfg.sim.poll_interval_s, queue,
                          host=cfg.modbus.host, port=cfg.modbus.port)
    writer = TelemetryWriter(connect, PointRegistry(cfg.site.code))
    stop_at = cfg.sim.start + timedelta(hours=hours)
    log.info("simulating %s from %s to %s at %gx", cfg.site.code, cfg.sim.start, stop_at,
             cfg.sim.time_scale)

    await field.start()
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(writer.run(queue))
            await poller.run(stop_at)
            await queue.put(None)             # tell the writer we're done
    finally:
        poller.close()
        await field.stop()

    log.info("done: %d cycles, %d rows written, %d spooled, %d dropped, missed polls %s",
             poller.cycles, writer.rows_written, writer.rows_spooled, writer.rows_dropped,
             dict(poller.missed))


async def field_main(config_path: Path) -> None:
    """Run only the field devices, until Ctrl+C. Any Modbus client can poll them."""
    cfg = load(config_path)
    clock = SimClock(cfg.sim.start, cfg.sim.time_scale)
    devices = build_plant(cfg)
    field = FieldServer(devices, clock, cfg.modbus.host, cfg.modbus.port)
    await field.start()
    for code, unit in unit_ids([d.code for d in devices]).items():
        log.info("unit %3d  %s", unit, code)
    try:
        await asyncio.Event().wait()          # wait forever
    finally:
        await field.stop()


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


def run_field() -> None:
    parser = argparse.ArgumentParser(description="Simulated field devices on Modbus TCP")
    parser.add_argument("--config", type=Path, default=Path("config/plant.toml"))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    try:
        asyncio.run(field_main(args.config))
    except KeyboardInterrupt:
        log.info("stopped by user")
