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
### Exercise 2.6 - Store and Forward
### Exercise 2.7 - Scale and connections
