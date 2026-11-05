"""Database connection and point-ID lookup (creating devices and points on first use)."""
from __future__ import annotations

import os
import re

import mariadb
from dotenv import find_dotenv, load_dotenv

_DEVICE_TYPE = re.compile(r"_([A-Z]{3})\d{2}$")      # SPS01_B02_INV03 -> "INV"


def connect() -> mariadb.Connection:
    load_dotenv(find_dotenv(usecwd=True))             # finds .env in a parent folder
    return mariadb.connect(
        host=os.environ.get("MARIADB_HOST", "127.0.0.1"),
        port=int(os.environ.get("MARIADB_PORT", "3306")),
        user=os.environ["MARIADB_USER"],
        password=os.environ["MARIADB_PASSWORD"],
        database=os.environ["MARIADB_DATABASE"],
        autocommit=False,
    )


class PointRegistry:
    """Maps (device code, point name) to point_id, with an in-memory cache."""

    def __init__(self, site_code: str) -> None:
        self.site_code = site_code
        self._ids: dict[tuple[str, str], int] = {}

    def clear(self) -> None:
        self._ids.clear()          # after a failed transaction, cached new IDs may not exist

    def point_id(self, cur: mariadb.Cursor, device: str, point: str) -> int:
        key = (device, point)
        if key not in self._ids:
            cur.execute("SELECT p.point_id FROM point p JOIN device d USING (device_id) "
                        "WHERE d.code = ? AND p.name = ?", key)
            row = cur.fetchone()
            if row is None:
                cur.execute("INSERT INTO point (device_id, name) VALUES (?, ?) RETURNING point_id",
                            (self._device_id(cur, device), point))
                row = cur.fetchone()
            self._ids[key] = row[0]
        return self._ids[key]

    def _device_id(self, cur: mariadb.Cursor, device: str) -> int:
        cur.execute("SELECT device_id FROM device WHERE code = ?", (device,))
        row = cur.fetchone()
        if row is None:
            match = _DEVICE_TYPE.search(device)
            if match is None:
                raise ValueError(f"{device!r} does not follow the naming standard")
            cur.execute("INSERT INTO device (site_id, device_type, code) "
                        "SELECT site_id, ?, ? FROM site WHERE code = ? RETURNING device_id",
                        (match.group(1), device, self.site_code))
            row = cur.fetchone()
            if row is None:
                raise LookupError(f"site {self.site_code!r} not found")
        return row[0]