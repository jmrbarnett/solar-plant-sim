"""Drain the reading queue into MariaDB in batches."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import mariadb

from plantsim.devices import Quality, Reading

log = logging.getLogger(__name__)

INSERT_SQL = ("INSERT INTO telemetry (point_id, ts, value, quality) VALUES (?, ?, ?, ?) "
              "ON DUPLICATE KEY UPDATE value = VALUES(value), quality = VALUES(quality)")
_NOTHING = object()       # marker: the queue wait timed out


class DbConnection(Protocol):
    """What the writer needs from a connection: a real mariadb one or a test fake."""
    def cursor(self, *, buffered: bool = ...) -> Any: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


class PointLookup(Protocol):
    """What the writer needs from the point registry: PointRegistry or a test fake."""
    def point_id(self, cur: Any, device: str, point: str) -> int: ...
    def clear(self) -> None: ...


class TelemetryWriter:
    def __init__(self, connect: Callable[[], DbConnection], registry: PointLookup,
                 batch_size: int = 500, flush_interval_s: float = 2.0, max_retries: int = 3,
                 spool_path: Path = Path("spool.jsonl")) -> None:
        self._connect = connect
        self.registry = registry
        self.batch_size = batch_size
        self.flush_interval_s = flush_interval_s
        self.max_retries = max_retries
        self.rows_written = 0
        self.rows_dropped = 0
        self.spool_path = spool_path
        self.rows_spooled = 0

    async def run(self, queue: asyncio.Queue[Reading | None]) -> None:
        """Consume until a None sentinel arrives. Flushes when the batch is full or old."""
        batch: list[Reading] = []
        last_flush = time.monotonic()
        try:
            while True:
                wait = max(0.0, self.flush_interval_s - (time.monotonic() - last_flush))
                try:
                    item = await asyncio.wait_for(queue.get(), wait)
                except TimeoutError:
                    item = _NOTHING
                if item is None:                       # end of data
                    break
                if isinstance(item, Reading):          # skips the _NOTHING timeout marker
                    batch.append(item)
                due = time.monotonic() - last_flush >= self.flush_interval_s
                if len(batch) >= self.batch_size or due:
                    if batch:
                        await asyncio.to_thread(self._write_with_retry, batch)
                        batch = []
                    last_flush = time.monotonic()
        finally:
            if batch:                                  # end of data, Ctrl+C or error
                self._write_with_retry(batch)

    def _write_with_retry(self, batch: list[Reading]) -> None:
        for attempt in range(1, self.max_retries + 1):
            try:
                self._write(batch)
                self.rows_written += len(batch)
                log.info("wrote %d rows (total %d)", len(batch), self.rows_written)
                self._replay_spool()
                return
            except mariadb.Error as exc:
                self.registry.clear()
                log.error("write failed (attempt %d/%d): %s", attempt, self.max_retries, exc)
                time.sleep(2 ** attempt)             # 2, 4, 8 s; we're in a worker thread
        self._spool(batch)

    def _write(self, batch: list[Reading]) -> None:
        conn = self._connect()
        try:
            cur = conn.cursor(buffered=True)
            rows = [(self.registry.point_id(cur, r.device, r.point), r.ts, r.value, int(r.quality))
                    for r in batch]
            cur.executemany(INSERT_SQL, rows)
            conn.commit()
        except mariadb.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _spool(self, batch: list[Reading]) -> None:
        """Save a batch that could not be written, one JSON object per line."""
        try:
            with self.spool_path.open("a", encoding="utf-8") as f:
                for r in batch:
                    f.write(json.dumps({"device": r.device, "point": r.point,
                                        "ts": r.ts.isoformat(), "value": r.value,
                                        "quality": int(r.quality)}) + "\n")
        except OSError as exc:                       # disk full, permissions...: last resort
            self.rows_dropped += len(batch)
            log.critical("dropped %d rows: cannot spool (%s)", len(batch), exc)
            return
        self.rows_spooled += len(batch)
        log.warning("spooled %d rows to %s after %d failed attempts",
                    len(batch), self.spool_path, self.max_retries)

    def _replay_spool(self) -> None:
        """Write any spooled rows, then delete the spool file."""
        if not self.spool_path.exists():
            return
        with self.spool_path.open(encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        readings = [Reading(d["device"], d["point"], datetime.fromisoformat(d["ts"]),
                            d["value"], Quality(d["quality"])) for d in rows]
        try:
            for i in range(0, len(readings), self.batch_size):
                self._write(readings[i:i + self.batch_size])
        except mariadb.Error as exc:
            log.error("spool replay failed, will retry after the next write: %s", exc)
            return                                   # keep the file; try again later
        self.spool_path.unlink()
        self.rows_written += len(readings)
        log.info("replayed %d spooled rows from %s", len(readings), self.spool_path)
