"""
Modbus register maps: where each point lives in a device's holding registers.
One map per device type, kept in one place (point-naming standard, section 7).
Addresses are protocol addresses, counted from 0.
"""
from __future__ import annotations

import struct
from collections.abc import Sequence
from dataclasses import dataclass

_FORMAT = {"uint16": "H", "int16": "h", "uint32": "I", "int32": "i", "float32": "f"}


@dataclass(frozen=True)
class Reg:
    point: str          # standard point name
    address: int        # first register, counted from 0
    kind: str           # "uint16", "int16", "uint32", "int32" or "float32"
    scale: float = 1.0  # engineering value = raw integer x scale (ignored for float32)

    @property
    def size(self) -> int:
        """Number of 16-bit registers this point occupies."""
        return 1 if self.kind.endswith("16") else 2


REGISTER_MAPS: dict[str, tuple[Reg, ...]] = {
    "INV": (Reg("AC_P_KW", 0, "float32"),
            Reg("DC_P_KW", 2, "float32"),
            Reg("CAB_TEMP_C", 4, "int16", 0.1),
            Reg("OPER_ST", 5, "uint16")),
    "MTR": (Reg("AC_P_KW", 0, "float32"),),
    "MET": (Reg("POA_IRR_WM2", 0, "uint16", 0.1),
            Reg("AMB_TEMP_C", 1, "int16", 0.1),
            Reg("MOD_TEMP_C", 2, "int16", 0.1)),
    "TRK": (Reg("ANG_TGT_DEG", 0, "int16", 0.01),
            Reg("ANG_ACT_DEG", 1, "int16", 0.01),
            Reg("MODE_ST", 2, "uint16")),
}


def device_type(code: str) -> str:
    """'SPS01_B01_INV02' -> 'INV'."""
    return code.rsplit("_", 1)[-1][:3]


def block_size(regs: tuple[Reg, ...]) -> int:
    """Registers needed to hold the whole map, from address 0."""
    return max(r.address + r.size for r in regs)


def encode(reg: Reg, value: float) -> list[int]:
    """Engineering value -> 16-bit register words, big-endian (high word first)."""
    raw = value if reg.kind == "float32" else round(value / reg.scale)
    data = struct.pack(">" + _FORMAT[reg.kind], raw)       # raises struct.error if out of range
    return [int.from_bytes(data[i:i + 2], "big") for i in range(0, len(data), 2)]


def decode(reg: Reg, words: Sequence[int]) -> float:
    """16-bit register words -> engineering value."""
    data = b"".join(w.to_bytes(2, "big") for w in words)
    (raw,) = struct.unpack(">" + _FORMAT[reg.kind], data)
    return raw if reg.kind == "float32" else raw * reg.scale


def unit_ids(codes: list[str]) -> dict[str, int]:
    """Assign Modbus unit IDs 1, 2, 3... in device order."""
    if len(codes) > 247:
        raise ValueError(f"{len(codes)} devices: Modbus unit IDs only go up to 247")
    return {code: i for i, code in enumerate(codes, start=1)}
