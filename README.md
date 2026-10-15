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
```
1. start docker
2. docker compose up -d
3. activate venv
4. run python python/sim/generate_day.py
5. open mariadb and source db/queries/*.sql for each exercise

See the module-1-answers.md file for the results at the time this repo was updated
