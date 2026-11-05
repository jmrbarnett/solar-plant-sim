"""Tests for config.load (Exercise 2.3b)."""
from datetime import datetime

from plantsim import config

SMALL_TOML = """
[site]
code = "TST01"
ac_kw = 500
dc_kw = 650
blocks = 1
inverters_per_block = 2
inverter_rated_kw = 250

[sim]
start = "2026-10-10T12:00:00"
time_scale = 10
poll_interval_s = 5
seed = 7
"""


def test_load_reads_site_and_sim(tmp_path):
    path = tmp_path / "plant.toml"          # / joins paths in pathlib
    path.write_text(SMALL_TOML)

    cfg = config.load(path)

    assert cfg.site.code == "TST01"
    assert cfg.site.inverters_per_block == 2
    assert cfg.sim.start == datetime(2026, 10, 10, 12, 0)   # string became a datetime
    assert cfg.sim.seed == 7


def test_missing_faults_section_gives_defaults(tmp_path):
    path = tmp_path / "plant.toml"
    path.write_text(SMALL_TOML)

    cfg = config.load(path)

    assert cfg.faults.underperformer is None
    assert cfg.faults.comms_minutes == 0