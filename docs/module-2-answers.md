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
