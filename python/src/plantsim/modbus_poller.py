"""The SCADA side: a Poller whose _fetch is a real Modbus TCP read."""
from __future__ import annotations

import asyncio
from datetime import datetime

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from plantsim.clock import SimClock
from plantsim.devices import CommsError, Device, Reading
from plantsim.poller import Poller
from plantsim.registers import REGISTER_MAPS, block_size, decode, device_type, unit_ids


class ModbusPoller(Poller):
    def __init__(self, devices: list[Device], clock: SimClock, interval_s: float,
                 queue: asyncio.Queue[Reading | None], host: str = "127.0.0.1",
                 port: int = 5020, request_timeout_s: float = 0.5) -> None:
        super().__init__(devices, clock, interval_s, queue)
        self.units = unit_ids([d.code for d in self.devices])
        # One connection per device, as if each had its own IP address. A pymodbus
        # client sends one request at a time, so a shared one would poll in series.
        self.clients = {d.code: AsyncModbusTcpClient(host, port=port, timeout=request_timeout_s,
                                                     retries=0)
                        for d in self.devices}

    async def _fetch(self, dev: Device, t: datetime) -> list[Reading]:
        client = self.clients[dev.code]
        regs = REGISTER_MAPS[device_type(dev.code)]
        try:
            if not client.connected and not await client.connect():
                raise CommsError(f"{dev.code}: cannot connect")
            rr = await client.read_holding_registers(0, count=block_size(regs),
                                                     device_id=self.units[dev.code])
        except ModbusException as exc:                    # timeout, connection lost
            raise CommsError(f"{dev.code}: {exc}") from exc
        if rr.isError():                                  # the device answered with an exception
            raise CommsError(f"{dev.code}: Modbus exception {rr.exception_code}")
        return [Reading(dev.code, reg.point, t,
                        round(decode(reg, rr.registers[reg.address:reg.address + reg.size]), 3))
                for reg in regs]

    def close(self) -> None:
        for client in self.clients.values():
            client.close()
