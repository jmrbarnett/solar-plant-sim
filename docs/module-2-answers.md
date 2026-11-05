# Module 2 - Python for Field Telemetry

## Part A
### A1 - Concepts mapping to C++

### A2 - Traps
1. Mutable default arguments are shared.
2. Assignments never copy
3. is vs ==
4. Truthiness (0, 0.0, "", [], {}, and None)
5. Closures bind late
### A3 - Idioms (used in the module)
1. Comprehensions: build collections in one expression
2. Unpacking
3. Context manager
4. Type hints (Pylance flag mismatches)

### A4 - Drills
#### 1. Write a comprehension that returns every inverter code from codes above that is in block 2
##### Begin with codes and narrow list by block (block = 2)
codes = [f"SPS01_B{b:02d}_INV{i:02d}" for b in (1, 2) for i in range(1, 5)]
print(f"Full codes list: {codes}")
b2_codes = [inv for inv in codes if '_B02_' in inv]
print(f"Codes for only block 2: {b2_codes}")
#### 2. Given samples = [("INV01", 240.1), ("INV02", 0.0), ("INV03", None)], build a dict of code → value that keeps the 0.0 and drops the None.
##### Now narrow a list into a dictionary as long as a value is available
sample = [("INV01", 240.1), ("INV02", 0.0), ("INV03", None)]
print(f"Starting list: {sample}")
my_dict = {}
for idx in sample:
    if idx[1] is not None:
        my_dict[idx[0]] = idx[1]
print(f"Ending dictionary w/no unreported values: {my_dict}")
#### 3. Write a generator minutes(start, end) that yields one datetime per minute, half-open like your SQL ranges.
##### Generator that yields one datetime per minute based on the start and end
from datetime import datetime, timedelta
def minutes(start:datetime, end:datetime):
    t = start
    while t < end:
        yield t
        print(t)
        t += timedelta(minutes=1)
##### Extra capture minutes output into a list and print just the times from that list
my_list = list(minutes(datetime(2026,10,9,17,0), datetime(2026,10,9,17,5)))
print([t.strftime("%H:%M") for t in my_list])
#### 4. Make a frozen dataclass Point(device: str, name: str, unit: str) and use instances as dict keys. Then try changing a field and read the error.
##### Make a frozen dataclass to use as a key into a dictionary. Try changing a value and observe the error
from dataclasses import dataclass, FrozenInstanceError
@dataclass(frozen=True)
#@dataclass()    # Produces TypeError: cannot use 'Point' as a set element (unhashable type: 'Point')
class point():
    device: str
    name: str
    unit: str
point1 = point("A", "Apple", "slice")
point2 = point("O", "Orange", "wedge")
fruitbasket = {point1,point2}
print(fruitbasket)
##### Expect the exception to trigger due to frozen setting on dataclass
try:
    point2.unit = "section"     # Triggers an exception!!
except FrozenInstanceError as exc:
    print("encountered FrozenInstanceError")
#### 5. Predict, then run: x = [[0] * 3] * 2; x[0][0] = 1; print(x). Explain the result with A2 trap 2.
##### Look at creating and setting cells in the matrix
x = [[0] * 3] * 2
x[1][1] = 7
print(x)
##### A matrix cannot be define if you want unique rows. This is the "assignment never copies" trap
#####  The assignment simply gives a new 'name'... reference actually for the original row and does
#####  not create a new unique row. Therefore changing one row changes all rows since there is only one
y = [[0] * 3 for _ in range(2)]
y[0][2] = 10
print(y)
##### 0 can be shared because it is immutable, if it was not, you would need another layer of
#####  definition to have unique rows and columns
lst = "mystr"
#z = [[lst] * 3 for _ in range(2)]
z = [[lst] * 3] * 2
print(z)
z[0][0] = "newstr"
priSnt(z)

## Part B
Set up directory structure and copied the configuration *.py files into place
Use pip install -e ".[dev]" to utilize pyproject.toml instead of requirements.txt to list dependencies
plant.toml sets up default values for runtime using tomllib
__init__.py sets up the plant simulator version
config.py declares configuration dataclasses (frozen) for different scenerios
All *.py need to use logging rather than print to provide feedback

## Part C
Copied device models *.py files into place including clock.py, weather.py, and devices.py
Design points
    • state() vs read() separates physics from communications. state() is what the equipment is doing; read() is what SCADA receives. The meter calls inv.state(), so it still sees an inverter whose comms are down, exactly the lesson from Exercise 1.5.
    • State is cached per timestamp. The meter and the poller both ask an inverter for 17:05; the random scatter must be drawn once, or the meter total won't match the inverters.
    • Each inverter gets its own Random. Results stay repeatable from the seed, whatever order the async poller happens to read devices in.
    • Temperature loss is new. At noon the modules run near 60 °C, about 12% below their 25 °C rating. Expect a lower Performance Ratio than Module 1's 0.922 (Exercise 2.2).
    • The template method pattern: Device.read() holds the common logic and calls the abstract _compute() that each subclass supplies. The leading underscore marks it internal by convention; Python doesn't enforce private.

## Part D
Concurrency and the async poller
Using asyncio in poller.py
    How it works
    • asyncio.TaskGroup starts one task per device and waits for all of them before the block ends, like spawning threads and joining them all. It's structured concurrency: no task can outlive the cycle that started it.
    • _poll_one catches its own errors. In a TaskGroup, an unhandled exception cancels every sibling task. One dead inverter must never stop the others from being polled.
    • asyncio.wait_for(..., timeout) gives each device its own deadline. A hung device costs at most 2 seconds and is counted in missed, not waited on forever.
    • The timestamp t is the scheduled poll time, not the moment each reply arrived. All devices in a cycle share one timestamp, which keeps your SQL comparisons (fleet median per ts) working.
    • asyncio.Queue(maxsize=...) provides backpressure. If the database slows down, the queue fills and put() waits, so the poller slows instead of eating all memory. That's a bounded buffer, the same idea as a ring buffer between threads in C.
    • Schedule from a fixed timeline (t += interval), never sleep(interval) after each cycle; otherwise each cycle's duration accumulates as drift.

## Part E
Writing to MariaDB
    Design notes:
    • Flush on size or age: a full batch (500 rows) goes immediately; a partial batch waits at most 2 seconds. That's the classic latency-vs-efficiency trade-off.
    • asyncio.to_thread runs the blocking MariaDB call in a worker thread, so the event loop keeps polling while the insert runs.
    • The None sentinel tells the writer that no more data is coming, and the finally block guarantees the last partial batch is written, even on Ctrl+C.
    • ON DUPLICATE KEY UPDATE makes reruns safe (idempotent), as in Exercise 1.4.
    • A connection per flush is simple and robust, and fine every few seconds. Real services use a connection pool; that's Exercise 2.7.
    • Dropping after 3 retries is a known weakness. A real historian buffers to disk instead ("store and forward"); Exercise 2.6.

## Exercises and checkpoint
### Exercise 2.1 - Drills
(see Part A4 - Drills)
### Exercise 2.2 - Run and Verify
Following initial run:
    MariaDB [plant]> select device, point, count(*) as samples
    -> from v_tlm
    -> where ts >= '2026-10-10' and ts < '2026-10-11'
    -> group by device, point
    -> order by device, point;
+-----------------+-------------+---------+
| device          | point       | samples |
+-----------------+-------------+---------+
| SPS01_B01_INV01 | AC_P_KW     |     720 |
| SPS01_B01_INV01 | CAB_TEMP_C  |     720 |
| SPS01_B01_INV01 | DC_P_KW     |     720 |
| SPS01_B01_INV01 | OPER_ST     |     720 |
| SPS01_B01_INV02 | AC_P_KW     |     700 |
| SPS01_B01_INV02 | CAB_TEMP_C  |     700 |
| SPS01_B01_INV02 | DC_P_KW     |     700 |
| SPS01_B01_INV02 | OPER_ST     |     700 |
| SPS01_B01_INV03 | AC_P_KW     |     720 |
| SPS01_B01_INV03 | CAB_TEMP_C  |     720 |
| SPS01_B01_INV03 | DC_P_KW     |     720 |
| SPS01_B01_INV03 | OPER_ST     |     720 |
| SPS01_B01_INV04 | AC_P_KW     |     720 |
| SPS01_B01_INV04 | CAB_TEMP_C  |     720 |
| SPS01_B01_INV04 | DC_P_KW     |     720 |
| SPS01_B01_INV04 | OPER_ST     |     720 |
| SPS01_B02_INV01 | AC_P_KW     |     720 |
| SPS01_B02_INV01 | CAB_TEMP_C  |     720 |
| SPS01_B02_INV01 | DC_P_KW     |     720 |
| SPS01_B02_INV01 | OPER_ST     |     720 |
| SPS01_B02_INV02 | AC_P_KW     |     720 |
| SPS01_B02_INV02 | CAB_TEMP_C  |     720 |
| SPS01_B02_INV02 | DC_P_KW     |     720 |
| SPS01_B02_INV02 | OPER_ST     |     720 |
| SPS01_B02_INV03 | AC_P_KW     |     720 |
| SPS01_B02_INV03 | CAB_TEMP_C  |     720 |
| SPS01_B02_INV03 | DC_P_KW     |     720 |
| SPS01_B02_INV03 | OPER_ST     |     720 |
| SPS01_B02_INV04 | AC_P_KW     |     720 |
| SPS01_B02_INV04 | CAB_TEMP_C  |     720 |
| SPS01_B02_INV04 | DC_P_KW     |     720 |
| SPS01_B02_INV04 | OPER_ST     |     720 |
| SPS01_MET01     | AMB_TEMP_C  |     720 |
| SPS01_MET01     | MOD_TEMP_C  |     720 |
| SPS01_MET01     | POA_IRR_WM2 |     720 |
| SPS01_MTR01     | AC_P_KW     |     720 |
+-----------------+-------------+---------+
36 rows in set (0.024 sec)

Module 1 Query against data on 2026-10-09
MariaDB [plant]> source db/queries/1_5_performance_ratio.sql
+----------+--------------+----------------+-------+
| e_ac_kwh | h_poa_kwh_m2 | dc_capacity_kw | pr    |
+----------+--------------+----------------+-------+
|   9389.2 |        3.917 |         2600.0 | 0.922 |
+----------+--------------+----------------+-------+
Update 1_5_performance_ratio.sql in two places to point to 2026-10-10 then run it:
MariaDB [plant]> source db/queries/1_5_performance_ratio.sql
+----------+--------------+----------------+-------+
| e_ac_kwh | h_poa_kwh_m2 | dc_capacity_kw | pr    |
+----------+--------------+----------------+-------+
|   9453.6 |        4.254 |         2600.0 | 0.855 |
+----------+--------------+----------------+-------+
1 row in set (0.002 sec)

AC energy for the inverters is calculated in devices.py adding a temperature factor into the dc value.
    g = weather.poa_wm2(t)
    temp_factor = 1 + TEMP_COEFF_PER_C * (self.weather.module_temp_c(t) - 25)   # TEMP_COEFF_PER_C = -0.0035
    dc = (self.dc_kw *
        g / 1000 *                                  # weather poa_wm2
        temp_factor *                               # See above
        self.derate *                               # derate = 1 unless specified in plant.toml
        self._rng.uniform(0.98, 1.0))               # small random scatter
    ac = min(self.rated_kw, dc * INVERTER_EFF)      # clipping INVERTER_EFF = 0.975

The decreased PR compared to Module 1 is due to considering the temperature affects on the panels among other factors.
Although the irradiance is larger on 2026-10-10 than on 2026-10-09, the increase in AC power is not as much as would be expected if the temperature didn't degrade the output.

Rerunning the exact Module 2 day (same seed, same clouds) with the losses switched off one at a time yields the following:
Run	                                    E_AC (kWh)	H_POA (kWh/m²)	PR
-----------------------------------------------------------------------------
As built (temperature loss + clipping)	  9,454	      4.254	        0.855
No temperature loss	                     10,104	      4.254	        0.914
No clipping	                              9,454	      4.254	        0.855
Neither	                                 10,188	      4.254	        0.921

Temperature accounts for essentially the whole drop. Switching it off adds about 650 kWh and raises PR from 0.855 to 0.914, about 6.5% in the 6–9% range for real plants. More sunlight also means hotter panels, and hotter panels convert sunlight less efficiently, although irradiance rose 8.6% the ac energy rose by much less (0.7%).

Losses Interact: Clipping cost nothing in the as-built run, but about 84 kWh when temperature loss was off. Hot panels produce less DC power, so the inverters rarely reached their 250 kW limit. Real loss budgets have to account for this overlap; you can’t simply add up each loss as if the others weren’t there.

### Exercise 2.3 - Grow the test suite
a. Weather returns 0 at night and its cloud factor stays between 0.3 and 1.0 over a simulated day
    Create test_weather.py that checks poa_wm2
    1. 0 at night and greater than 0 during the day
    2. Stays between 0.3 and 1.0 for all times during the day
    3. For good measure make sure the poa_wm2 is never negative
b. config.load on a small TOML file written with pytest's built-in tmp_path fixture
    Create test_config.py that uses pytest's built-in fixture tmp_path to execute using a different .toml file
c. the writer flushes a full batch, using a fake connect function that records executemany calls instead of touching MariaDB. Run coverage and note what remains untested.
    Create test_writer.py
============================================= tests coverage ===============================================
_______________________________ coverage: platform linux, python 3.14.4-final-0 ____________________________

Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
src/plantsim/__init__.py       1      0   100%
src/plantsim/clock.py         11      0   100%
src/plantsim/config.py        39      1    97%   50
    Not tested: The comms_start string-to-datetime conversion
    Worth testing from 2.3b; writing it brings coverage to 100%
src/plantsim/db.py            37     25    32%   14-15, 29-30, 33, 36-46, 49-61
    Not tested: connect() and PointRegistry lookups and inserts. They need a real MariaDB
    Worth an integration test using the real DB in Docker. Separate from the fast unit tests.
src/plantsim/devices.py       70      0   100%
src/plantsim/main.py          55     55     0%   2-78
    Not tested: The program's entry point: reads the config, wires together and runs
    Not worth a unit test. It's glue code; an end-to-end run against the database covers it.
src/plantsim/poller.py        48      1    98%   54
    Not tested: The poller is behind schedule warning.
    Low priority for testing
src/plantsim/weather.py       33      2    94%   47, 50
    Not tested ambient_c and module_temp_c. The device tests use FakeWeather so the real ones never run
    Quick to add
src/plantsim/writer.py        66     11    83%   41-42, 64-69, 79-81
    Not tested: queue_wait timeout branch. Tests queued everything up front so the wait never times out
    Optional for testing
    Not tested: The retry and drop path: what happens when Maria DB raises an error
    Most important untested code; Exercise 2.6 (store and forward) changes it
--------------------------------------------------------
TOTAL                        360     95    74%
============================================= 20 passed in 0.22s ==============================================
Takeaways:
    * Coverage shows what ran, not what was checked. A line can be covered by a test that asserts nothing about it. 100% isn’t the goal; the important paths are.
    * The biggest real gap is error handling (writer retries), which is typical. Failure paths need deliberately injected failures, such as a fake connection that raises mariadb.Error.
    * Database code needs a different kind of test. That’s normal, not a flaw in the suite.

### Exercise 2.4 - Communication status point
Added COMM_ST as a Point for all devices in poller.py

Created 2_4_comms_outages.sql that identifies an outage as follows:
MariaDB [plant]> source db/queries/2_4_comms_outages.sql;
+-----------------+-------------------------+-------------------------+---------+
| device          | outage_start            | outage_end              | minutes |
+-----------------+-------------------------+-------------------------+---------+
| SPS01_B01_INV02 | 2026-10-10 17:00:00.000 | 2026-10-10 17:20:00.000 |      20 |
+-----------------+-------------------------+-------------------------+---------+
1 row in set (0.005 sec)

A row can be missing from telemetry for several reasons (the poller crashed, the database was down, or the device stopped responding) and they all look the same. Recording comms status explicitly as COMM_ST removes that ambiguity, separates a loss of visibility from a loss of power, and gives alarms and queries a value to act on.

### Exercise 2.5 - Tracker controllers
Added a Tracker device to devices.py. Included a clamp function to limit the range of a float, a TrackerMode enum, and the Tracker class itself.

Changed _hour() in Weather to be a module-level function called utc_hour() so I could use that in the Tracker class code (also import of utc_hour). Also added sunrise_utc and sunset_utc to tests/fakes.py to keep it up to date with the changes.

Added stuck_tracker and stuck_tracker_from to FaultConfig and included the stuck_tracker_from in the faults list in the load function in config.py.

Modified build_plant in main.py to include a list of trackers similar to inverters. Included the import of Tracker and returned the trackers list along with the other devices.

Added the two lines to plant.toml to designate SPS01_B01_TRK03 as a tracker stuck from 18:00 for our tests.

Added the following tests to test_devices.py to address the tracker:
    test_tracker_follows_the_sun (parameterized with 11 scenarios to cover different times)
    test_healthy_tracker_stays_close_to_target
    test_stuck_tracker_holds_zero_from_fault_time
    test_tracker_points

Ran
    pytest -v (resulting in 34 passed tests to verify that functions performed as expected before running plantsim)
    plantsim --hours 12 (to fill the DB with the new data that included the trackers)

Created two query files that ran as follows:

MariaDB [plant]> source db/queries/count_samples_in_telemetry.sql
+-------------+---------+---------+
| device_type | devices | samples |
+-------------+---------+---------+
| INV         |       8 |   28720 |
| MTR         |       1 |    1440 |
| MET         |       1 |    2880 |
| TRK         |       8 |   23040 |
+-------------+---------+---------+
4 rows in set (0.031 sec)

MariaDB [plant]> source db/queries/2_5_stuck_tracker.sql
+-----------------+-------------------------+-------------------------+-------------+---------------+
| device          | first_flagged           | last_flagged            | minutes_off | max_error_deg |
+-----------------+-------------------------+-------------------------+-------------+---------------+
| SPS01_B01_TRK03 | 2026-10-10 18:00:00.000 | 2026-10-10 22:59:00.000 |         300 |          60.0 |
+-----------------+-------------------------+-------------------------+-------------+---------------+
1 row in set (0.016 sec)

Using the actual vs the target values for the angles can detect a stuck tracker, however, because of the
+/- 5 degree tolerance there will be a blind spot for detecting near the angle that it is stuck at. From
the 15 degrees per hour movement and the band going from -5 to +5 around the stuck angle, there is a 40-minute timeframe where it's impossible to tell a stuck tracker from a healthy one. A tracker stuck at 0 degrees is the hardest to detect because 0 is a legitimate value for both noon and all through the night when the panels stow.

### Exercise 2.6 - Store and Forward
Prior to this exercise the v_tlm sample count is as follows:
MariaDB [plant]> select count(*) from v_tlm;
+----------+
| count(*) |
+----------+
|    94900 |
+----------+
1 row in set (0.008 sec)

After clearing the DB of any 10-10-2026 data:
MariaDB [plant]> select count(*) from v_tlm;
+----------+
| count(*) |
+----------+
|    38820 |
+----------+
1 row in set (0.004 sec)

After re-running plantsim for the 12 hours on 10-10-2026 and cycling the database with docker compose stop db, docker compose start db, approx 30 seconds apart the count is as follows:
MariaDB [plant]> select count(*) from v_tlm;
+----------+
| count(*) |
+----------+
|    94244 |
+----------+
1 row in set (0.023 sec)

The significant portions of the log read as follows:
...
2026-11-04 12:21:29,360 INFO     plantsim.writer: wrote 156 rows (total 3822)
2026-11-04 12:21:31,374 INFO     plantsim.writer: wrote 156 rows (total 3978)
2026-11-04 12:21:33,376 ERROR    plantsim.writer: write failed (attempt 1/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 12:21:35,376 ERROR    plantsim.writer: write failed (attempt 2/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 12:21:39,378 ERROR    plantsim.writer: write failed (attempt 3/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 12:21:47,378 CRITICAL plantsim.writer: dropped 156 rows after 3 attempts
2026-11-04 12:21:47,380 ERROR    plantsim.writer: write failed (attempt 1/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 12:21:49,381 ERROR    plantsim.writer: write failed (attempt 2/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 12:21:53,382 ERROR    plantsim.writer: write failed (attempt 3/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 12:22:01,382 CRITICAL plantsim.writer: dropped 500 rows after 3 attempts
2026-11-04 12:22:01,386 ERROR    plantsim.writer: write failed (attempt 1/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 12:22:03,387 ERROR    plantsim.writer: write failed (attempt 2/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 12:22:07,440 INFO     plantsim.writer: wrote 500 rows (total 4478)
2026-11-04 12:22:07,445 INFO     plantsim.writer: wrote 500 rows (total 4978)
...
2026-11-04 12:26:39,720 INFO     plantsim.writer: wrote 156 rows (total 27346)
2026-11-04 12:26:40,787 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:00:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:41,730 INFO     plantsim.writer: wrote 152 rows (total 27498)
2026-11-04 12:26:41,782 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:01:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:42,788 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:02:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:43,737 INFO     plantsim.writer: wrote 148 rows (total 27646)
2026-11-04 12:26:43,780 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:03:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:44,810 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:04:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:45,744 INFO     plantsim.writer: wrote 148 rows (total 27794)
2026-11-04 12:26:45,817 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:05:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:46,815 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:06:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:47,753 INFO     plantsim.writer: wrote 148 rows (total 27942)
2026-11-04 12:26:47,809 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:07:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:48,781 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:08:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:49,762 INFO     plantsim.writer: wrote 148 rows (total 28090)
2026-11-04 12:26:49,807 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:09:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:50,796 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:10:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:51,772 INFO     plantsim.writer: wrote 148 rows (total 28238)
2026-11-04 12:26:51,793 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:11:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:52,798 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:12:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:53,780 INFO     plantsim.writer: wrote 148 rows (total 28386)
2026-11-04 12:26:53,785 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:13:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:54,798 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:14:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:55,790 INFO     plantsim.writer: wrote 148 rows (total 28534)
2026-11-04 12:26:55,792 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:15:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:56,801 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:16:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:57,799 INFO     plantsim.writer: wrote 163 rows (total 28697)
2026-11-04 12:26:57,801 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:17:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:58,781 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:18:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:59,788 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:19:00 failed: SPS01_B01_INV02: no response
2026-11-04 12:26:59,807 INFO     plantsim.writer: wrote 186 rows (total 28883)
...
2026-11-04 12:32:39,816 INFO     plantsim.writer: wrote 156 rows (total 55424)
2026-11-04 12:32:39,816 INFO     plantsim: done: 720 cycles, 55424 rows written, 656 dropped, missed polls {'SPS01_B01_INV02': 20}

Still showing the failed responses built into SPS01_B01_INV02 with additional values missing for every device. We see this using data_gaps.sql modified to use 10-10-2026 instead of 10-9-2026:

MariaDB [plant]> source db/queries/data_gaps.sql
+-----------------+-------------+-------------------------+-------------------------+-------+
| device          | point       | gap_start               | gap_end                 | gap_s |
+-----------------+-------------+-------------------------+-------------------------+-------+
| SPS01_B01_INV01 | AC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_INV01 | OPER_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_INV01 | DC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_INV01 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_INV01 | CAB_TEMP_C  | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_INV02 | OPER_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV02 | DC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV02 | CAB_TEMP_C  | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV02 | AC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV02 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV02 | CAB_TEMP_C  | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
| SPS01_B01_INV02 | AC_P_KW     | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
| SPS01_B01_INV02 | OPER_ST     | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
| SPS01_B01_INV02 | DC_P_KW     | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
| SPS01_B01_INV03 | CAB_TEMP_C  | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV03 | AC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV03 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV03 | OPER_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV03 | DC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV04 | AC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV04 | CAB_TEMP_C  | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV04 | DC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV04 | OPER_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_INV04 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_TRK01 | MODE_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_TRK01 | ANG_TGT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_TRK01 | ANG_ACT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_TRK01 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B01_TRK02 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_TRK02 | ANG_TGT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_TRK02 | ANG_ACT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_TRK02 | MODE_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_TRK03 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_TRK03 | ANG_TGT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_TRK03 | ANG_ACT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_TRK03 | MODE_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_TRK04 | ANG_ACT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_TRK04 | MODE_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_TRK04 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B01_TRK04 | ANG_TGT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B02_INV01 | CAB_TEMP_C  | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV01 | AC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV01 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV01 | DC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV01 | OPER_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV02 | CAB_TEMP_C  | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV02 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV02 | AC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV02 | OPER_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV02 | DC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV03 | CAB_TEMP_C  | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B02_INV03 | AC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B02_INV03 | OPER_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B02_INV03 | DC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B02_INV03 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B02_INV04 | AC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV04 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV04 | CAB_TEMP_C  | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV04 | DC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_INV04 | OPER_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK01 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK01 | ANG_ACT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK01 | ANG_TGT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK01 | MODE_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK02 | MODE_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B02_TRK02 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B02_TRK02 | ANG_TGT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B02_TRK02 | ANG_ACT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_B02_TRK03 | ANG_ACT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK03 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK03 | MODE_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK03 | ANG_TGT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK04 | ANG_TGT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK04 | MODE_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK04 | ANG_ACT_DEG | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_B02_TRK04 | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 11:59:00.000 |   540 |
| SPS01_MET01     | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_MET01     | MOD_TEMP_C  | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_MET01     | POA_IRR_WM2 | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_MET01     | AMB_TEMP_C  | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_MTR01     | AC_P_KW     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
| SPS01_MTR01     | COMM_ST     | 2026-10-10 11:50:00.000 | 2026-10-10 12:00:00.000 |   600 |
+-----------------+-------------+-------------------------+-------------------------+-------+
82 rows in set (0.037 sec)

Rerunning with the store and forward updates results in...
pytest returns 35 tests passed
cleared DB of 10-10 data 38820 count for v_tlm
...
2026-11-04 16:56:03,401 INFO     plantsim.writer: wrote 156 rows (total 1638)
2026-11-04 16:56:05,409 ERROR    plantsim.writer: write failed (attempt 1/3): Server has gone away
2026-11-04 16:56:07,410 ERROR    plantsim.writer: write failed (attempt 2/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 16:56:11,410 ERROR    plantsim.writer: write failed (attempt 3/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 16:56:19,412 WARNING  plantsim.writer: spooled 156 rows to spool.jsonl after 3 failed attempts
2026-11-04 16:56:19,415 ERROR    plantsim.writer: write failed (attempt 1/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 16:56:21,416 ERROR    plantsim.writer: write failed (attempt 2/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 16:56:25,416 ERROR    plantsim.writer: write failed (attempt 3/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 16:56:33,418 WARNING  plantsim.writer: spooled 500 rows to spool.jsonl after 3 failed attempts
2026-11-04 16:56:33,422 ERROR    plantsim.writer: write failed (attempt 1/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 16:56:35,421 ERROR    plantsim.writer: write failed (attempt 2/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 16:56:39,422 ERROR    plantsim.writer: write failed (attempt 3/3): Can't connect to server on '127.0.0.1' (115)
2026-11-04 16:56:47,423 WARNING  plantsim.writer: spooled 500 rows to spool.jsonl after 3 failed attempts
2026-11-04 16:56:47,425 ERROR    plantsim.writer: write failed (attempt 1/3): Lost connection to server at 'handshake: reading initial communication packet', system error: 11
2026-11-04 16:56:49,446 INFO     plantsim.writer: wrote 500 rows (total 2138)
2026-11-04 16:56:49,463 INFO     plantsim.writer: replayed 1156 spooled rows from spool.jsonl
2026-11-04 16:56:49,469 INFO     plantsim.writer: wrote 500 rows (total 3794)
...
same outages on SPS01_B01_INV02
...
2026-11-04 17:07:42,222 INFO     plantsim.writer: wrote 78 rows (total 56080)
2026-11-04 17:07:42,223 INFO     plantsim: done: 720 cycles, 56080 rows written, 1156pooled, 0 dropped, missed polls {'SPS01_B01_INV02': 20}

Note the 0 dropped records and 1156 spooled (went more than 30 seconds this time)
The handshake error depends on the timing of exactly when the DB goes offline and back online. MariaDB was not ready for the login yet when plantsim attempted to reconnect. This is not a problem and cleared right away on the next write.
MariaDB [plant]> select count(*) from v_tlm;
+----------+
| count(*) |
+----------+
|    94900 |
+----------+
1 row in set (0.006 sec)
Matches the numbers from before the dropped DB
MariaDB [plant]> source db/queries/data_gaps.sql
+-----------------+------------+-------------------------+-------------------------+-------+
| device          | point      | gap_start               | gap_end                 | gap_s |
+-----------------+------------+-------------------------+-------------------------+-------+
| SPS01_B01_INV02 | CAB_TEMP_C | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
| SPS01_B01_INV02 | AC_P_KW    | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
| SPS01_B01_INV02 | DC_P_KW    | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
| SPS01_B01_INV02 | OPER_ST    | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
+-----------------+------------+-------------------------+-------------------------+-------+
4 rows in set (0.053 sec)
MariaDB [plant]> source db/queries/2_4_comms_outages.sql
+-----------------+-------------------------+-------------------------+---------+
| device          | outage_start            | outage_end              | minutes |
+-----------------+-------------------------+-------------------------+---------+
| SPS01_B01_INV02 | 2026-10-10 17:00:00.000 | 2026-10-10 17:20:00.000 |      20 |
+-----------------+-------------------------+-------------------------+---------+
1 row in set (0.021 sec)

The query for data gaps returns only the original planned fault outages and COMM_ST is not among the missing points listed. Looking further we see that COMM_ST values of 0 (lost) are present for every minute in the gap, therefore, we know that there is a comms outage for SPS01_B01_INV02.

### Exercise 2.7 - Scale and connections
Created plant_large.toml to increase the number of blocks from 2 to 50, set ac_kw and dc_kw to 50,000 and 65,000 respectively, and removed all the fault definitions since they were unnecessary. Ran the following command:
plantsim --config config/plant_large.toml --hours 1 --verbose 2>&1 | grep -E "cycle|behind"
and found cycles to be between 0.051 to 0.054 seconds with the final message
2026-11-05 10:23:51,449 INFO     plantsim: done: 60 cycles, 108360 rows written, 0 spooled, 0 dropped, missed polls {}

Changed poller.py to poll each device in serial and re-ran the same test
the cycles now range from 12.016 to 12.920 seconds
Each write is followed by a message from the poller that it is behind, growing by around 11.4 seconds each cycle to a final reported lag of 673.2 seconds over the course of one simulated hour (not including the final cycle).
2026-11-05 13:25:01,897 INFO     plantsim: done: 60 cycles, 108360 rows written, 0 spooled, 0 dropped, missed polls {}

The concurrent polling is significantly more efficient and necessary for processing the data in real time. The poller does not need to wait for a response before polling the next device. The average cycle time is closer to the response time for the slowest single device instead of the sum of the response times for each polled device. A twelve second delay when polling every device once is untenable when polling must be done every second (running at 60x speed).

Update to writer.py to keep the connection and only reconnect after an error. Ran pytest with new test with 36 passed.
Then executed a shorter run on 10-10-2026 (plant.toml) for just one hour:
plantsim --hours 1 --verbose 2>&1 | grep -E "connected|done", resulting in:
2026-11-05 11:30:45,481 INFO     plantsim.writer: connected to database
2026-11-05 11:31:42,522 INFO     plantsim: done: 60 cycles, 4680 rows written, 0 spooled, 0 dropped, missed polls {}
This confirms that the connection was opened once for the full hour of data

Next, rerun the 2.6 outage test using the following steps:
1. Clear October 10: DELETE FROM telemetry WHERE ts >= '2026-10-10' AND ts < '2026-10-11';
2. Run plantsim --hours 12, and stop and start the database partway through.

plantsim --hours 12
2026-11-05 12:05:33,536 INFO     plantsim: simulating SPS01 from 2026-10-10 11:00:00 to 2026-10-10 23:00:00 at 60x
2026-11-05 12:05:35,542 INFO     plantsim.writer: connected to database
2026-11-05 12:05:35,564 INFO     plantsim.writer: wrote 156 rows (total 156)
2026-11-05 12:05:37,597 INFO     plantsim.writer: wrote 182 rows (total 338)
...
Connect to database only once at the start of the run - not for each write:

The output around when the DB was stopped and restarted:
...
2026-11-05 12:06:32,309 INFO     plantsim.writer: wrote 156 rows (total 4602)
2026-11-05 12:06:34,311 ERROR    plantsim.writer: write failed (attempt 1/3): Lost connection to server during query
2026-11-05 12:06:36,312 ERROR    plantsim.writer: write failed (attempt 2/3): Can't connect to server on '127.0.0.1' (115)
2026-11-05 12:06:40,313 ERROR    plantsim.writer: write failed (attempt 3/3): Can't connect to server on '127.0.0.1' (115)
2026-11-05 12:06:48,314 WARNING  plantsim.writer: spooled 156 rows to spool.jsonl after 3 failed attempts
2026-11-05 12:06:48,318 ERROR    plantsim.writer: write failed (attempt 1/3): Can't connect to server on '127.0.0.1' (115)
2026-11-05 12:06:50,319 ERROR    plantsim.writer: write failed (attempt 2/3): Can't connect to server on '127.0.0.1' (115)
2026-11-05 12:06:54,320 ERROR    plantsim.writer: write failed (attempt 3/3): Can't connect to server on '127.0.0.1' (115)
2026-11-05 12:07:02,323 WARNING  plantsim.writer: spooled 500 rows to spool.jsonl after 3 failed attempts
2026-11-05 12:07:02,325 ERROR    plantsim.writer: write failed (attempt 1/3): Can't connect to server on '127.0.0.1' (115)
2026-11-05 12:07:04,327 ERROR    plantsim.writer: write failed (attempt 2/3): Can't connect to server on '127.0.0.1' (115)
2026-11-05 12:07:08,327 ERROR    plantsim.writer: write failed (attempt 3/3): Can't connect to server on '127.0.0.1' (115)
2026-11-05 12:07:16,329 WARNING  plantsim.writer: spooled 500 rows to spool.jsonl after 3 failed attempts
2026-11-05 12:07:16,332 ERROR    plantsim.writer: write failed (attempt 1/3): Can't connect to server on '127.0.0.1' (115)
2026-11-05 12:07:18,332 ERROR    plantsim.writer: write failed (attempt 2/3): Can't connect to server on '127.0.0.1' (115)
2026-11-05 12:07:22,334 ERROR    plantsim.writer: write failed (attempt 3/3): Lost connection to server at 'handshake: reading initial communication packet', system error: 11
2026-11-05 12:07:30,336 WARNING  plantsim.writer: spooled 500 rows to spool.jsonl after 3 failed attempts
2026-11-05 12:07:30,348 INFO     plantsim.writer: connected to database
2026-11-05 12:07:30,371 INFO     plantsim.writer: wrote 500 rows (total 5102)
2026-11-05 12:07:30,392 INFO     plantsim.writer: replayed 1656 spooled rows from spool.jsonl
2026-11-05 12:07:30,397 INFO     plantsim.writer: wrote 500 rows (total 7258)
2026-11-05 12:07:30,402 INFO     plantsim.writer: wrote 500 rows (total 7758)
...
Note the "connected to database" appears once just before resumed writes and the replay of spooled data

The output around the planned faults:
...
2026-11-05 12:11:31,956 INFO     plantsim.writer: wrote 156 rows (total 28002)
2026-11-05 12:11:33,556 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:00:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:33,966 INFO     plantsim.writer: wrote 152 rows (total 28154)
2026-11-05 12:11:34,552 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:01:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:35,569 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:02:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:36,007 INFO     plantsim.writer: wrote 148 rows (total 28302)
2026-11-05 12:11:36,572 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:03:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:37,545 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:04:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:38,015 INFO     plantsim.writer: wrote 148 rows (total 28450)
2026-11-05 12:11:38,563 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:05:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:39,550 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:06:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:40,035 INFO     plantsim.writer: wrote 148 rows (total 28598)
2026-11-05 12:11:40,539 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:07:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:41,566 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:08:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:42,042 INFO     plantsim.writer: wrote 148 rows (total 28746)
2026-11-05 12:11:42,558 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:09:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:43,563 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:10:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:44,050 INFO     plantsim.writer: wrote 148 rows (total 28894)
2026-11-05 12:11:44,541 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:11:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:45,566 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:12:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:46,059 INFO     plantsim.writer: wrote 148 rows (total 29042)
2026-11-05 12:11:46,576 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:13:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:47,557 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:14:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:48,067 INFO     plantsim.writer: wrote 148 rows (total 29190)
2026-11-05 12:11:48,559 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:15:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:49,557 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:16:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:50,078 INFO     plantsim.writer: wrote 148 rows (total 29338)
2026-11-05 12:11:50,547 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:17:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:51,579 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:18:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:52,086 INFO     plantsim.writer: wrote 148 rows (total 29486)
2026-11-05 12:11:52,540 WARNING  plantsim.poller: poll SPS01_B01_INV02 @ 2026-10-10 17:19:00 failed: SPS01_B01_INV02: no response
2026-11-05 12:11:54,096 INFO     plantsim.writer: wrote 152 rows (total 29638)
2026-11-05 12:11:56,104 INFO     plantsim.writer: wrote 156 rows (total 29794)
...
No change from previous run

...
2026-11-05 12:17:32,575 INFO     plantsim: done: 720 cycles, 56080 rows written, 1656 spooled, 0 dropped, missed polls {'SPS01_B01_INV02': 20}
The final line confirms 12 hours of data (720 cycles) produced 56080 rows. 1656 were spooled, 0 dropped, and 20 missing polls as expected.

Including all the rows added to the telemetry we should see 203260 rows:
Day	                                    Rows
October 9 (Module 1)	                38,820
October 10 (normal plant, 12 hours)	    56,080
October 11 (large plant, 1 hour)	    108,360
Total	                                203,260
MariaDB [plant]> select count(*) from v_tlm;
+----------+
| count(*) |
+----------+
|   203260 |
+----------+
1 row in set (0.017 sec)

Re-running the queries we ran for 2.6 identifying the outages we see:
MariaDB [plant]> source db/queries/data_gaps.sql;
+-----------------+------------+-------------------------+-------------------------+-------+
| device          | point      | gap_start               | gap_end                 | gap_s |
+-----------------+------------+-------------------------+-------------------------+-------+
| SPS01_B01_INV02 | AC_P_KW    | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
| SPS01_B01_INV02 | CAB_TEMP_C | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
| SPS01_B01_INV02 | DC_P_KW    | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
| SPS01_B01_INV02 | OPER_ST    | 2026-10-10 16:59:00.000 | 2026-10-10 17:20:00.000 |  1260 |
+-----------------+------------+-------------------------+-------------------------+-------+
4 rows in set (0.068 sec)
MariaDB [plant]> source db/queries/2_4_comms_outages.sql
+-----------------+-------------------------+-------------------------+---------+
| device          | outage_start            | outage_end              | minutes |
+-----------------+-------------------------+-------------------------+---------+
| SPS01_B01_INV02 | 2026-10-10 17:00:00.000 | 2026-10-10 17:20:00.000 |      20 |
+-----------------+-------------------------+-------------------------+---------+
1 row in set (0.011 sec)
The both queries show only the planned INV02 outage.
