# Solar Plant Simulator

## Module 1 - Development Environment and MariaDB

### Project Modules
|--------------------------------|      |-----------------------------|     |-------------------------------|
| Python Field Simulators        |      | Industrial protocols        |     | Ignition 8.3 Gateway          |
|  Inverters, meter, met station |----->|  Modbus TCP, OPC-UA         |---->|  Tags, alarms, historian, HMI |
| Modules 1 & 2                  |      | Module 3                    |     | Modules 4 & 5                 |
|--------------------------------|      |-----------------------------|     |-------------------------------|
        |                                                                                     |
        |                                             historian and named queries             |
        |       |-----------------------------------------------------------------------------|
        |       | 
        v       v
|--------------------------------|      |-----------------------------|     |-------------------------------|
| MariaDB 12.3                   |      | Node.js API                 |     | Angular Dashboard             |
|  Telemetry + historian tables  |----->|  REST + WebSocket Live Feed |---->|  Plant KPIs in the browser    |
| Module 1                       |      | Module 6                    |     | Module 7                      |
|--------------------------------|      |-----------------------------|     |-------------------------------|

### Project layout
```
solar-plant-sim/
├── docker-compose.yml    # MariaDB (later Ignition, API, web)
├── .env                  # secrets, never committed
├── db/init/              # SQL run on first container start
├── db/queries/           # KPI queries
├── python/sim/           # telemetry generator
├── ignition/             # Ignition project (Modules 4–5)
├── api/                  # Node.js API (Module 6)
└── web/                  # Angular dashboard (Module 7)
```
## Module 2 - Python for Field Telemetry

## Python Modules
                          read()              asyncio.Queue               executemany
|-------------------------|   |--------------------|   |---------------------|   |------------------|
| Field Devices           |   | Poller             |   | Telemetry           |   | MariaDB          |
| 8 inverters, meter,     |   | Reads every device |   | Batches readings,   |   | telemetry table, |
| met station, shared     |-->| each sim minute,   |-->| inserts in a worker |-->| new points added |
| weather model           |   | all in parallel    |   | thread, retries     |   | on first use     |
| weather.py & devices.py |   | poller.py          |   | writer.py & db.py   |   | Docker:plant-db  |
|-------------------------|   |--------------------|   |---------------------|   |------------------|

### Project layout
'''
python/
├── .venv/
├── pyproject.toml            # replaces requirements.txt
├── config/
│   └── plant.toml            # site, simulation and fault settings
├── src/
│   └── plantsim/
│       ├── __init__.py
│       ├── clock.py          # accelerated simulation time
│       ├── config.py         # loads plant.toml into dataclasses
│       ├── weather.py        # sun, clouds, temperatures
│       ├── devices.py        # Inverter, Meter, MetStation
│       ├── poller.py         # async polling
│       ├── db.py             # connection + point registry
│       ├── writer.py         # batching database writer
│       └── main.py           # wiring + command line
├── tests/
│   ├── test_devices.py
│   └── test_poller.py
└── sim/
    └── generate_day.py       # Module 1, unchanged
'''

## How to Run
Set up Environment to Run
    With docker installed, from the start menu start docker
    Open Ubuntu shell
        cd ~/src/solar-plant-sim
        code .
    in VS Code terminal window 
        docker compose up -d
        docker compose ps       # wait for healthy DB
        cd python
        source .venv/bin/activate

Module 1: 
    python python/sim/generate_day.py
    
    To look at DB
        mariadb -h 127.0.0.1 -u plant_app -p plant     # enter the plant_app user's password
        source db_queries/*.sql associated with each exercise as needed
        to modify the partitions of telemetry in exercise 1.8 use db/migrations/001_p2027_01.sql

Module 2: (presupposes that Module 1 has been run successfully)
    plantsim --hours 12        # 12 simulated hours = 12 real minutes
