"""Tests for TelemetryWriter batching (Exercise 2.3c). No database needed."""
import asyncio
from datetime import datetime, timedelta

from plantsim.devices import Quality, Reading
from plantsim.writer import TelemetryWriter

T0 = datetime(2026, 10, 10, 17, 0)


class FakeCursor:
    def __init__(self, calls):
        self.calls = calls                       # shared list owned by FakeConnection

    def executemany(self, sql, rows):
        self.calls.append(list(rows))            # record instead of inserting


class FakeConnection:
    """Stands in for a mariadb connection; remembers what was done to it."""
    def __init__(self):
        self.executemany_calls = []
        self.commits = 0
        self.closed = False

    def cursor(self, buffered=False):
        return FakeCursor(self.executemany_calls)

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def close(self):
        self.closed = True


class FakeRegistry:
    """Hands out a stable integer id per (device, point), like PointRegistry."""
    def __init__(self):
        self.ids = {}

    def point_id(self, cur, device, point):
        return self.ids.setdefault((device, point), len(self.ids) + 1)

    def clear(self):
        self.ids.clear()


def make_readings(n):
    return [Reading("SPS01_B01_INV01", "AC_P_KW", T0 + timedelta(minutes=i), 100.0 + i)
            for i in range(n)]


async def run_writer(readings, batch_size):
    conn = FakeConnection()
    writer = TelemetryWriter(lambda: conn, FakeRegistry(),
                             batch_size=batch_size, flush_interval_s=60.0)
    queue = asyncio.Queue()
    for r in readings:
        await queue.put(r)
    await queue.put(None)                        # end-of-data sentinel
    await writer.run(queue)
    return writer, conn


async def test_full_batch_is_flushed_then_remainder_at_end():
    writer, conn = await run_writer(make_readings(4), batch_size=3)

    sizes = [len(call) for call in conn.executemany_calls]
    assert sizes == [3, 1]                       # one full batch, then the leftover
    assert writer.rows_written == 4
    assert writer.rows_dropped == 0


async def test_rows_carry_point_id_timestamp_value_and_quality():
    writer, conn = await run_writer(make_readings(3), batch_size=3)

    first_row = conn.executemany_calls[0][0]
    assert first_row == (1, T0, 100.0, int(Quality.GOOD))   # (point_id, ts, value, quality)
    assert conn.commits == 1
    assert conn.closed