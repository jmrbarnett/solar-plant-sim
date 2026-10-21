"""Load plant.toml into typed, read-only configuration objects."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SiteConfig:
    code: str
    ac_kw: float
    dc_kw: float
    blocks: int
    inverters_per_block: int
    inverter_rated_kw: float


@dataclass(frozen=True)
class SimConfig:
    start: datetime
    time_scale: float
    poll_interval_s: float
    seed: int


@dataclass(frozen=True)
class FaultConfig:
    underperformer: str | None = None
    underperformer_derate: float = 1.0
    comms_device: str | None = None
    comms_start: datetime | None = None
    comms_minutes: int = 0


@dataclass(frozen=True)
class Config:
    site: SiteConfig
    sim: SimConfig
    faults: FaultConfig


def load(path: Path) -> Config:
    with path.open("rb") as f:
        raw = tomllib.load(f)
    sim = raw["sim"]
    faults = dict(raw.get("faults", {}))
    if "comms_start" in faults:
        faults["comms_start"] = datetime.fromisoformat(faults["comms_start"])
    return Config(
        site=SiteConfig(**raw["site"]),
        sim=SimConfig(
            start=datetime.fromisoformat(sim["start"]),
            time_scale=sim["time_scale"],
            poll_interval_s=sim["poll_interval_s"],
            seed=sim["seed"],
        ),
        faults=FaultConfig(**faults),
    )