# Module 2 - Python for Field Telemetry

## Part A
### A2 - Traps
1. Mutable default arguments are shared. 
2. Assignments never copy
3. is vs ==
4. Truthiness (0, 0.0, "", [], {}, and None)
5. Closures bind late
### A3 - Idioms (used in the module)
1. Comprehensions: build collections in one expression
2. Unpacking
3. Contect manager
4. Type hints (Pylance flag mismatches)
### A4 - Drills
1. 
#### Begin with codes and narrow list by block (block = 2)
codes = [f"SPS01_B{b:02d}_INV{i:02d}" for b in (1, 2) for i in range(1, 5)]
print(f"Full codes list: {codes}")
b2_codes = [inv for inv in codes if '_B02_' in inv]
print(f"Codes for only block 2: {b2_codes}")
2. 
#### Now narrow a list into a dictionary as long as a value is available
sample = [("INV01", 240.1), ("INV02", 0.0), ("INV03", None)]
print(f"Starting list: {sample}")
my_dict = {}
for idx in sample: 
    if idx[1] is not None:
        my_dict[idx[0]] = idx[1]
print(f"Ending dictionary w/no unreported values: {my_dict}")
3. 
#### Generator that yields one datetime per minute based on the start and end
from datetime import datetime, timedelta
def minutes(start:datetime, end:datetime):
    t = start
    while t < end:
        yield t
        print(t)
        t += timedelta(minutes=1)
#### Extra capture minutes output into a list and print just the times from that list
my_list = list(minutes(datetime(2026,10,9,17,0), datetime(2026,10,9,17,5)))
print([t.strftime("%H:%M") for t in my_list])
4. 
#### Make a frozen dataclass to use as a key into a dictionary. Try changing a value and observe the error
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
#### Expect the exception to trigger due to frozen setting on dataclass
try:
    point2.unit = "section"     # Triggers an exception!!
except FrozenInstanceError as exc:
    print("encoutered FrozenInstanceError")
5. 
#### Look at creating and setting cells in the matrix
x = [[0] * 3] * 2
x[1][1] = 7
print(x)
#### A matrix cannot be define if you want unique rows. This is the "assignment never copies" trap
####  The assignment simply gives a new 'name'... reference actually for the original row and does
####  not create a new unique row. Therefore changing one row changes all rows since there is only one
y = [[0] * 3 for _ in range(2)]
y[0][2] = 10
print(y)
#### 0 can be shared because it is immutable, if it was not, you would need another layer of 
####  definition to have unique rows and columns
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


