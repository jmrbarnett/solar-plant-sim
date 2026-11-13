"""The field side: simulated devices served over Modbus TCP, one unit ID per device."""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime
from functools import partial

from pymodbus.constants import ExcCodes
from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

from plantsim.clock import SimClock
from plantsim.devices import CommsError, Device
from plantsim.registers import REGISTER_MAPS, block_size, device_type, encode, unit_ids

log = logging.getLogger(__name__)


class FieldServer:
    def __init__(self, devices: list[Device], clock: SimClock, host: str = "127.0.0.1",
                 port: int = 5020, latency_s: tuple[float, float] = (0.01, 0.05),
                 rng: random.Random | None = None) -> None:
        self.clock = clock
        self.latency_s = latency_s
        self._rng = rng or random.Random()
        units = unit_ids([d.code for d in devices])
        sim_devices = [
            SimDevice(units[d.code],
                      SimData(0, count=block_size(REGISTER_MAPS[device_type(d.code)]),
                              datatype=DataType.REGISTERS, readonly=True),
                      action=partial(self._on_read, d))
            for d in devices
        ]
        self._server = ModbusTcpServer(sim_devices, address=(host, port))
        self.address = (host, port)

    async def _on_read(self, dev: Device, function_code: int, start_address: int,
                       address: int, count: int, registers: list[int],
                       set_values: list[int] | list[bool] | None) -> ExcCodes | None:
        """Called by pymodbus for every request to this device, before it answers."""
        await asyncio.sleep(self._rng.uniform(*self.latency_s))    # device response time
        t: datetime = self.clock.now().replace(second=0, microsecond=0)
        try:
            readings = dev.read(t)
        except CommsError:
            return ExcCodes.GATEWAY_NO_RESPONSE    # the gateway can't reach this device
        values = {r.point: r.value for r in readings}
        for reg in REGISTER_MAPS[device_type(dev.code)]:
            i = reg.address - start_address
            registers[i:i + reg.size] = encode(reg, values[reg.point])
        return None

    async def start(self) -> None:
        """Start listening; returns once the port is open."""
        await self._server.serve_forever(background=True)
        log.info("field devices listening on %s:%d", *self.address)

    async def stop(self) -> None:
        await self._server.shutdown()
