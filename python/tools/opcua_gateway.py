"""A tiny Modbus-to-OPC UA gateway: polls two points from the field devices and serves
them as OPC UA variables. Ignition does the same job, at scale, in Module 4."""
import asyncio
import logging

from asyncua import Server
from pymodbus.client import AsyncModbusTcpClient

from plantsim.registers import REGISTER_MAPS, decode

MODBUS_PORT = 5020
ENDPOINT = "opc.tcp://127.0.0.1:4840/plantsim/"
NAMESPACE = "urn:plantsim"
POINTS = [("SPS01_MTR01", "MTR", 17, "AC_P_KW"),      # device, type, unit ID, point
          ("SPS01_MET01", "MET", 18, "POA_IRR_WM2")]


async def main() -> None:
    server = Server()
    await server.init()
    server.set_endpoint(ENDPOINT)
    server.set_server_name("plantsim OPC UA gateway")
    ns = await server.register_namespace(NAMESPACE)
    site = await server.nodes.objects.add_folder(ns, "SPS01")
    variables = {}
    for device, _, _, point in POINTS:
        obj = await site.add_object(ns, device)
        variables[(device, point)] = await obj.add_variable(ns, point, 0.0)

    modbus = AsyncModbusTcpClient("127.0.0.1", port=MODBUS_PORT, timeout=1, retries=0)
    await modbus.connect()
    async with server:
        logging.info("serving %s", ENDPOINT)
        while True:
            for device, dtype, unit, point in POINTS:
                reg = next(r for r in REGISTER_MAPS[dtype] if r.point == point)
                rr = await modbus.read_holding_registers(reg.address, count=reg.size, device_id=unit)
                if not rr.isError():
                    await variables[(device, point)].write_value(decode(reg, rr.registers))
            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s")
    logging.getLogger("asyncua").setLevel(logging.ERROR)
    asyncio.run(main())
