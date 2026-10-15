# Solar Plant Simulator
## Project layout

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
## How to Run

1. start docker
2. docker compose up -d
3. activate venv
4. run python python/sim/generate_day.py
5. open mariadb and source db/queries/*.sql for each exercise
6. to modify the partitions of telemetry in exercise 1.8 use db/migrations/001_p2027_01.sql

See the docs/module-1-answers.md file for the results at the time this module was completed
