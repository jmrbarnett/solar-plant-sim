"""Register encoding tests (Module 3)."""
import struct

import pytest

from plantsim.registers import REGISTER_MAPS, Reg, block_size, decode, device_type, encode, unit_ids


def test_float32_is_two_words_high_word_first():
    reg = Reg("AC_P_KW", 0, "float32")
    assert encode(reg, 250.0) == [0x437A, 0x0000]      # IEEE 754: 250.0 = 0x437A0000
    assert decode(reg, [0x437A, 0x0000]) == 250.0


def test_scaled_int16_round_trips_to_its_resolution():
    reg = Reg("CAB_TEMP_C", 4, "int16", 0.1)
    assert encode(reg, 54.79) == [548]                 # 54.79 / 0.1 = 547.9, rounds to 548
    assert decode(reg, [548]) == pytest.approx(54.8)


def test_negative_int16_is_twos_complement():
    reg = Reg("ANG_ACT_DEG", 1, "int16", 0.01)
    assert encode(reg, -2.5) == [0xFF06]               # -250 as 16 bits
    assert decode(reg, [0xFF06]) == pytest.approx(-2.5)


def test_value_out_of_range_is_an_error():
    with pytest.raises(struct.error):
        encode(Reg("X", 0, "int16", 0.01), 400.0)      # 40000 doesn't fit in int16


def test_maps_do_not_overlap():
    for dtype, regs in REGISTER_MAPS.items():
        used = [a for r in regs for a in range(r.address, r.address + r.size)]
        assert len(used) == len(set(used)), dtype
        assert block_size(regs) == len(used), dtype     # no gaps either


def test_device_type_and_unit_ids():
    assert device_type("SPS01_B01_INV02") == "INV"
    assert device_type("SPS01_MTR01") == "MTR"
    assert unit_ids(["A", "B"]) == {"A": 1, "B": 2}
    with pytest.raises(ValueError):
        unit_ids([f"D{i}" for i in range(248)])
