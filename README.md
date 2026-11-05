# Solar Plant Simulator

## Module 1 - Development Environment and MariaDB

### Project Modules
```
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
```
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
```
                          read()              asyncio.Queue               executemany
|-------------------------|   |--------------------|   |---------------------|   |------------------|
| Field Devices           |   | Poller             |   | Telemetry           |   | MariaDB          |
| 8 inverters, meter,     |   | Reads every device |   | Batches readings,   |   | telemetry table, |
| met station, shared     |-->| each sim minute,   |-->| inserts in a worker |-->| new points added |
| weather model           |   | all in parallel    |   | thread, retries     |   | on first use     |
| weather.py & devices.py |   | poller.py          |   | writer.py & db.py   |   | Docker:plant-db  |
|-------------------------|   |--------------------|   |---------------------|   |------------------|
```
### Project layout
```
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
```

## How to Run
## Setup (once)

Prerequisites: WSL2 Ubuntu, Docker Desktop, Python 3.12+, and the MariaDB client,
and the build tools for the mariadb Python package

```bash
sudo apt install -y python3-venv python3-pip mariadb-client libmariadb-dev gcc python3-dev
```

```bash
cd ~/src/solar-plant-sim
cp .env.example .env              # then set the passwords in .env
docker compose up -d              # first start runs db/init/*.sql
docker compose ps                 # wait until plant-db is healthy

cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"           # editable install + test tools; creates the plantsim command
```

## Each session

```bash
cd ~/src/solar-plant-sim
docker compose up -d
cd python
source .venv/bin/activate
```

## Module 1: generate one day of data

From the repo root, with the venv active:

```bash
python python/sim/generate_day.py
mariadb -h 127.0.0.1 -u plant_app -p plant      # then: source db/queries/<file>.sql
```

## Module 2: run the simulator

From `python/`:

```bash
plantsim --hours 12                                  # 11:00–23:00 UTC on 2026-10-10; 12 real minutes
plantsim --config config/plant_large.toml --hours 1  # 402 devices on 2026-10-11
plantsim --hours 1 --verbose                         # DEBUG output, including cycle times
```

Faults in `config/plant.toml`: underperformer SPS01_B02_INV03, comms outage on
SPS01_B01_INV02 (17:00–17:20), and tracker SPS01_B01_TRK03 stuck from 18:00.
If the database is unavailable, failed batches are saved to `spool.jsonl` and
replayed automatically once writes succeed again.

## Testing

From `python/` (pytest reads its settings from `pyproject.toml` there):

```bash
pytest                                               # 36 tests
pytest --cov=plantsim --cov-report=term-missing      # with coverage
```
