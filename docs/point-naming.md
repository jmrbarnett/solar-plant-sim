# Solar Plant Simulator — Point Naming Standard

**Scope:** every device and point in the Solar Plant Simulator (`solar-plant-sim`): the MariaDB
`device` and `point` tables, the Python simulators, and (from Module 4) Ignition tags and UDTs.

> This is a teaching standard modeled on common industry practice. Real owners, NextEra
> included, maintain their own internal standards; expect the structure to be similar and the
> exact codes to differ. Point vocabulary is aligned with SunSpec where an equivalent exists —
> check the SunSpec model definitions before relying on any mapping in production.

---

## 1. Why a naming standard

- **One query, screen or template serves every device.** `WHERE point = 'AC_P_KW'` finds AC
  power on every inverter and meter, whatever the vendor.
- **Names are self-describing.** An operator reading `SPS01_B02_INV03 / DC_P_KW` at 2 a.m. knows
  the site, block, device and measurement without a lookup.
- **Vendors disagree.** Inverter A calls it `Pac`, B calls it `ActivePower`, C uses SunSpec `W`.
  The standard maps all of them to one internal name at the integration layer.
- **Tools depend on it.** Ignition UDTs, alarm pipelines and reports are built from the name
  pattern; inconsistent names break them silently.

## 2. General rules

| Rule                                           | Example               | Reason                                                        |
|------------------------------------------------|-----------------------|---------------------------------------------------------------|
| Upper case letters, digits and `_` only        | `SPS01_B02_INV03`     | Valid in SQL, Python, Ignition and file names without quoting |
| No spaces, dashes or dots                      | ~~`SPS01-B02.INV 3`~~ | Dashes and dots have meaning in tag paths and SQL             |
| Fixed-width numbers, zero-padded               | `INV03`, not `INV3`   | Sorts correctly; constant length                              |
| Numbering starts at 01                         | `B01`, `INV01`        | Matches field labels; 00 reserved (see §3)                    |
| Units are part of the point name               | `AC_P_KW`, not `AC_P` | The unit is never ambiguous, even in a CSV export             |
| Maximum length: device 32, point 32 characters | —                     | Matches the `device.code` and `point.name` columns            |
| Names are permanent                            | —                     | Renaming breaks history; retire and replace instead           |

## 3. Device names

```
<SITE>_<AREA><NN>_<TYPE><NN>        block-level device    SPS01_B02_INV03
<SITE>_<TYPE><NN>                   site-level device     SPS01_MTR01
```

| Part   | Format               | Meaning                          | Examples                |
|--------|----------------------|----------------------------------|-------------------------|
| `SITE` | 3 letters + 2 digits | Site code                        | `SPS01` (Sunshine PV 1) |
| `AREA` | Letter + 2 digits    | Block / power-conversion station | `B01`, `B02`            |
| `TYPE` | 2–4 letters          | Device type (table below)        | `INV`, `MTR`, `TRK`     |
| `NN`   | 2 digits             | Instance within its area         | `01`–`99`               |

Site-level devices (revenue meter, plant controller, substation) omit the area part.

### Device type codes

| Code  | Device                                          | Level        |
|-------|-------------------------------------------------|--------------|
| `INV` | PV inverter                                     | Block        |
| `CMB` | DC combiner box                                 | Block        |
| `TRK` | Tracker controller (one per row or row group)   | Block        |
| `XFM` | Transformer (block step-up or main)             | Block / site |
| `MET` | Meteorological station                          | Block / site |
| `PCS` | Battery power conversion system (BESS inverter) | Block        |
| `BAT` | Battery bank / rack group                       | Block        |
| `MTR` | Meter (revenue at POI, or check meter)          | Site         |
| `PPC` | Power plant controller                          | Site         |
| `BRK` | Breaker                                         | Site         |
| `RLY` | Protective relay                                | Site         |

## 4. Point names

```
<DOMAIN>_<QUANTITY>[_<QUALIFIER>]_<UNIT>
```

| Part        | Meaning                               | Values                                                               |
|-------------|---------------------------------------|----------------------------------------------------------------------|
| `DOMAIN`    | Where the quantity is measured        | `AC`, `DC`, `POA`, `GHI`, `AMB`, `MOD`, `CAB`, `BAT`, …              |
| `QUANTITY`  | What is measured                      | `P` (real power), `Q` (reactive), `S` (apparent),                    |
|             |                                       | `V`, `I`, `F` (frequency), `PF`, `E` (energy), `IRR` (irradiance),   |
|             |                                       | `TEMP`, `SOC`, `ANG` (angle)                                         |
| `QUALIFIER` | Optional: phase, direction, statistic | `A`/`B`/`C`, `AB`, `EXP`/`IMP`, `TGT`/`ACT`, `MAX`                   |
| `UNIT`      | Engineering unit                      | `KW`, `KVAR`, `KVA`, `V`, `A`, `HZ`, `KWH`, `WM2`, `C`, `PCT`, `DEG` |

Points that are not measurements end with a role suffix instead of a unit:

| Suffix | Role                              | Example                                         |
|--------|-----------------------------------|-------------------------------------------------|
| `_ST`  | State (enumerated status)         | `OPER_ST` — 1 = running, 2 = standby, 3 = fault |
| `_ALM` | Alarm / fault word                | `FAULT_ALM`                                     |
| `_SP`  | Setpoint (writeable target)       | `P_LIM_SP_KW`                                   |
| `_CMD` | Command (writeable action)        | `STOW_CMD`                                      |
| `_FB`  | Feedback of a command or setpoint | `P_LIM_FB_KW`                                   |

### Sign conventions

- **Real power:** positive = generation exported to the grid; negative = import (e.g. night-time
  auxiliary load, battery charging).
- **Reactive power:** positive = exporting vars (over-excited / capacitive).
- **Tracker angle:** 0° = flat; negative = facing east; positive = facing west.

## 5. Full tag path

In the database the device and point are separate columns. Elsewhere they combine into a path:

| System                       | Format                           | Example                      |
|------------------------------|----------------------------------|------------------------------|
| MariaDB                      | `device.code` + `point.name`     | `SPS01_B02_INV03`, `AC_P_KW` |
| Ignition tag path (Module 4) | `<SITE>/<AREA>/<DEVICE>/<POINT>` | `SPS01/B02/INV03/AC_P_KW`    |
| Flat export / CSV            | `<DEVICE>.<POINT>`               | `SPS01_B02_INV03.AC_P_KW`    |

In Ignition, each device type becomes a **UDT** (user-defined type) whose member tags are the
point names below, so one template defines every inverter.

## 6. Point lists by device type

### Inverter (`INV`)

| Point          | Unit | Description                               | SunSpec equivalent |
|----------------|------|-------------------------------------------|--------------------|
| `AC_P_KW`      | kW   | AC real power                             | `W`                |
| `AC_Q_KVAR`    | kvar | AC reactive power                         | `VAr`              |
| `AC_PF`        | —    | Power factor                              | `PF`               |
| `AC_F_HZ`      | Hz   | Grid frequency                            | `Hz`               |
| `AC_V_AB_V`    | V    | Line voltage A–B                          | `PPVphAB`          |
| `AC_E_KWH`     | kWh  | Lifetime energy counter                   | `WH`               |
| `COMM_ST`      | —    | 1 = communicating, 0 = lost               | **                 |
| `DC_P_KW`      | kW   | DC input power                            | `DCW`              |
| `DC_V_V`       | V    | DC input voltage                          | `DCV`              |
| `DC_I_A`       | A    | DC input current                          | `DCA`              |
| `CAB_TEMP_C`   | °C   | Cabinet temperature (simulator: `TEMP_C`) | `TmpCab`           |
| `OPER_ST`      | —    | Operating state                           | `St`               |
| `FAULT_ALM`    | —    | Fault / event bit-field                   | `Evt1`             |
| `P_LIM_SP_PCT` | %    | Active power limit setpoint               | `WMaxLimPct`       |


### Revenue meter (`MTR`)

| Point          | Unit | Description                 | SunSpec equivalent |
|----------------|------|-----------------------------|--------------------|
| `AC_P_KW`      | kW   | Net real power at POI       | `W`                |
| `AC_Q_KVAR`    | kvar | Net reactive power          | `VAR`              |
| `AC_PF`        | —    | Power factor                | `PF`               |
| `AC_F_HZ`      | Hz   | Frequency                   | `Hz`               |
| `AC_V_AB_V`    | V    | Line voltage A–B            | `PPVphAB`          |
| `AC_E_EXP_KWH` | kWh  | Energy exported (delivered) | `TotWhExp`         |
| `AC_E_IMP_KWH` | kWh  | Energy imported (received)  | `TotWhImp`         |
| `COMM_ST`      | —    | 1 = communicating, 0 = lost | **                 |

### Met station (`MET`)

| Point          | Unit | Description                  | SunSpec equivalent |
|----------------|------|------------------------------|--------------------|
| `COMM_ST`      | —    | 1 = communicating, 0 = lost  | **                 |
| `POA_IRR_WM2`  | W/m² | Plane-of-array irradiance    | `POAI`             |
| `GHI_IRR_WM2`  | W/m² | Global horizontal irradiance | `GHI`              |
| `AMB_TEMP_C`   | °C   | Ambient air temperature      | `TmpAmb`           |
| `MOD_TEMP_C`   | °C   | Back-of-module temperature   | `TmpBOM`           |
| `WIND_SPD_MS`  | m/s  | Wind speed                   | `WndSpd`           |
| `WIND_DIR_DEG` | °    | Wind direction               | `WndDir`           |
| `RH_PCT`       | %    | Relative humidity            | `RH`               |

** Produced by the poller, not read from the device, so every device has them even when it is not responding.
These points have no SunSpec equivalent; SunSpec defines only device-side registers.

### Tracker controller (`TRK`)

| Point           | Unit | Description                                                          |
|-----------------|------|----------------------------------------------------------------------|
| `ANG_TGT_DEG`   | °    | Target (commanded) angle                                             |
| `ANG_ACT_DEG`   | °    | Actual measured angle                                                |
| `ANG_ERR_DEG`   | °    | Target − actual (derived)                                            |
| `MODE_ST`       | —    | 1 = tracking, 2 = backtracking, 3 = wind stow, 4 = manual, 5 = fault |
| `MOTOR_ST`      | —    | Motor state                                                          |
| `BATT_V_V`      | V    | Controller backup battery voltage                                    |
| `WIND_STOW_ALM` | —    | Wind-stow active alarm                                               |
| `STOW_CMD`      | —    | Command: stow now                                                    |
| `FAULT_ALM`     | —    | Fault bit-field                                                      |

Example tags: `SPS01_B01_TRK07 / ANG_ACT_DEG`, `SPS01_B01_TRK07 / MODE_ST`.

### Battery inverter / PCS (`PCS`) and battery bank (`BAT`)

| Device | Point            | Unit | Description                               |
|--------|------------------|------|-------------------------------------------|
| `PCS`  | `AC_P_KW`        | kW   | Real power; + discharge to grid, − charge |
| `PCS`  | `AC_Q_KVAR`      | kvar | Reactive power                            |
| `PCS`  | `P_SP_KW`        | kW   | Real power setpoint from PPC              |
| `PCS`  | `P_FB_KW`        | kW   | Setpoint feedback                         |
| `PCS`  | `OPER_ST`        | —    | Operating state                           |
| `BAT`  | `BAT_SOC_PCT`    | %    | State of charge                           |
| `BAT`  | `BAT_SOH_PCT`    | %    | State of health                           |
| `BAT`  | `BAT_V_V`        | V    | DC bus voltage                            |
| `BAT`  | `BAT_I_A`        | A    | DC current; + discharge                   |
| `BAT`  | `BAT_TEMP_MAX_C` | °C   | Highest cell temperature                  |
| `BAT`  | `FAULT_ALM`      | —    | Fault bit-field                           |

Example tags: `SPS01_B03_PCS01 / P_SP_KW`, `SPS01_B03_BAT01 / BAT_SOC_PCT`.

## 7. Mapping vendor names

Field devices keep their native names. The integration layer (Python poller in Module 2,
Ignition device connection in Module 4) maps them on the way in:

| Vendor A register | Vendor B register | SunSpec  | **Standard point** |
|-------------------|-------------------|----------|--------------------|
| `Pac`             | `ActivePower`     | `W`      | `AC_P_KW`          |
| `Udc`             | `DcVoltage`       | `DCV`    | `DC_V_V`           |
| `Tint`            | `CabinetTemp`     | `TmpCab` | `CAB_TEMP_C`       |

Keep this mapping in one place (a table or a config file), never scattered through code.

## 8. Simulator conformance

The Module 1 simulator already follows this standard, with one exception kept for compatibility:

| Simulator point     | Standard name | Action                                           |
|---------------------|---------------|--------------------------------------------------|
| `TEMP_C` (inverter) | `CAB_TEMP_C`  | Rename in Module 2 when the simulator is rebuilt |

## 9. Change control

- New device types or point names are added to this document **before** they appear in code.
- Never reuse a retired name for a different meaning.
- Every change is a Git commit to `docs/point-naming.md` with a one-line reason.
