"""Seed a small PV plant and generate one day of 60 s telemetry into MariaDB.
Run against a fresh database (docker compose down -v && up -d)."""
import math
import os
import random
from datetime import datetime, timedelta
from dataclasses import dataclass

import mariadb
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

@dataclass(frozen=True)
class Site:
    code: str
    name: str
    lat: float
    lon: float
    ac_kw: float
    dc_kw: float
SITE = Site(code="SPS01", name="Sunshine PV 1", lat=26.89, lon=-80.06,
            ac_kw=2000.0, dc_kw=2600.0)           # DC/AC ratio 1.3
INV_RATED_KW = 250.0
BLOCKS, INV_PER_BLOCK = 2, 4
STEP_S = 60
SUNRISE_UTC, SUNSET_UTC = 11.3, 23.0             # mid-Oct, South Florida
UNDERPERFORMER = "SPS01_B02_INV03"               # planted fault: DC-side loss
GAP_DEVICE, GAP_START_H, GAP_MIN = "SPS01_B01_INV02", 17.0, 20  # planted comms gap


def connect():
    return mariadb.connect(
        host="127.0.0.1", port=3306,
        user=os.environ["MARIADB_USER"], password=os.environ["MARIADB_PASSWORD"],
        database=os.environ["MARIADB_DATABASE"], autocommit=False)


def seed(cur):
    """Insert site, devices and points. Returns inverter codes and a point lookup."""
    cur.execute(
        "INSERT INTO site (code, name, latitude, longitude, ac_capacity_kw, dc_capacity_kw) "
        "VALUES (?, ?, ?, ?, ?, ?) RETURNING site_id",
        (SITE.code, SITE.name, SITE.lat, SITE.lon, SITE.ac_kw, SITE.dc_kw))
    site_id = cur.fetchone()[0]
    points = {}                                   # (device_code, point_name) -> point_id

    def add_device(code, dtype, rated, ip):
        cur.execute(
            "INSERT INTO device (site_id, device_type, code, rated_kw, ip_addr, modbus_unit_id) "
            "VALUES (?, ?, ?, ?, ?, 1) RETURNING device_id",
            (site_id, dtype, code, rated, ip))
        return cur.fetchone()[0]

    def add_point(dev_id, dev_code, name, unit):
        cur.execute("INSERT INTO point (device_id, name, unit) VALUES (?, ?, ?) RETURNING point_id",
                    (dev_id, name, unit))
        points[(dev_code, name)] = cur.fetchone()[0]

    inverters = []
    for b in range(1, BLOCKS + 1):
        for i in range(1, INV_PER_BLOCK + 1):
            code = f"SPS01_B{b:02d}_INV{i:02d}"
            dev = add_device(code, "INV", INV_RATED_KW, f"10.10.{b}.{10 + i}")
            for name, unit in (("AC_P_KW", "kW"), ("DC_P_KW", "kW"), ("TEMP_C", "degC")):
                add_point(dev, code, name, unit)
            inverters.append(code)

    mtr = add_device("SPS01_MTR01", "MTR", None, "10.10.0.20")
    add_point(mtr, "SPS01_MTR01", "AC_P_KW", "kW")
    met = add_device("SPS01_MET01", "MET", None, "10.10.0.30")
    add_point(met, "SPS01_MET01", "POA_IRR_WM2", "W/m2")
    add_point(met, "SPS01_MET01", "AMB_TEMP_C", "degC")

    cur.execute("INSERT INTO plant_setpoint (site_id, p_limit_kw, updated_by) VALUES (?, ?, 'seed')",
                (site_id, SITE.ac_kw))
    return inverters, points


def poa_irradiance(hour, cloud):
    """Crude clear-sky bell curve scaled by a cloud factor, W/m2."""
    if not SUNRISE_UTC < hour < SUNSET_UTC:
        return 0.0
    x = (hour - SUNRISE_UTC) / (SUNSET_UTC - SUNRISE_UTC)
    return 1000.0 * math.sin(math.pi * x) ** 1.2 * cloud


def generate(day, inverters, points):
    rows = []
    dc_per_inv = SITE.dc_kw / len(inverters)
    cloud, t = 1.0, day
    while t < day + timedelta(days=1):
        hour = t.hour + t.minute / 60
        cloud = min(1.0, max(0.3, cloud + random.gauss(0, 0.03)))   # random walk
        g = poa_irradiance(hour, cloud)
        amb = 22 + 8 * max(0.0, math.sin(math.pi * (hour - 11) / 14))
        rows.append((points[("SPS01_MET01", "POA_IRR_WM2")], t, round(g, 1)))
        rows.append((points[("SPS01_MET01", "AMB_TEMP_C")], t, round(amb, 1)))

        plant_kw = 0.0
        for code in inverters:
            derate = 0.75 if code == UNDERPERFORMER else random.uniform(0.98, 1.0)
            dc = dc_per_inv * g / 1000 * derate
            ac = min(INV_RATED_KW, dc * 0.975)    # 97.5% efficiency, clips at rating
            plant_kw += ac                        # the meter still sees power during a comms gap
            if code == GAP_DEVICE and GAP_START_H <= hour < GAP_START_H + GAP_MIN / 60:
                continue                          # ...but the historian gets no samples
            rows.append((points[(code, "DC_P_KW")], t, round(dc, 2)))
            rows.append((points[(code, "AC_P_KW")], t, round(ac, 2)))
            rows.append((points[(code, "TEMP_C")], t, round(amb + ac / INV_RATED_KW * 25, 1)))

        rows.append((points[("SPS01_MTR01", "AC_P_KW")], t, round(plant_kw * 0.985, 2)))
        t += timedelta(seconds=STEP_S)
    return rows


def main():
    random.seed(42)                               # repeatable data
    day = datetime(2026, 10, 9)                   # naive datetime = UTC by convention
    conn = connect()
    try:
        cur = conn.cursor()
        inverters, points = seed(cur)
        rows = generate(day, inverters, points)
        for i in range(0, len(rows), 5000):
            cur.executemany("INSERT INTO telemetry (point_id, ts, value) VALUES (?, ?, ?)",
                            rows[i:i + 5000])
        conn.commit()
        print(f"Inserted {len(rows):,} telemetry rows for {day:%Y-%m-%d}")
    except mariadb.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()