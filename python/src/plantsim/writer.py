"""Drain the reading queue into MariaDB in batches."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

import mariadb

from plantsim.db import PointRegistry
from plantsim.devices import Reading

log = logging.getLogger(__name__)

INSERT_SQL = ("INSERT INTO telemetry (point_id, ts, value, quality) VALUES (?, ?, ?, ?) "
              "ON DUPLICATE KEY UPDATE value = VALUES(value), quality = VALUES(quality)")
_NOTHING = object()       # marker: the queue wait timed out


class TelemetryWriter:
    def __init__(self, connect: Callable[[], mariadb.Connection], registry: PointRegistry,
                 batch_size: int = 500, flush_interval_s: float = 2.0, max_retries: int = 3) -> None:
        self._connect = connect
        self.registry = registry
        self.batch_size = batch_size
        self.flush_interval_s = flush_interval_s
        self.max_retries = max_retries
        self.rows_written = 0
        self.rows_dropped = 0

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
                return
            except mariadb.Error as exc:
                self.registry.clear()
                log.error("write failed (attempt %d/%d): %s", attempt, self.max_retries, exc)
                time.sleep(2 ** attempt)             # 2, 4, 8 s; we're in a worker thread
        self.rows_dropped += len(batch)
        log.critical("dropped %d rows after %d attempts", len(batch), self.max_retries)

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