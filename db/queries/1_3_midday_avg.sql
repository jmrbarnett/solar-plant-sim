-- =============================================================
-- Exercise 1.3: Find the planted faults
-- Purpose : Get the average power output for each device 
--           during the midday period (3pm to 9pm)
-- Expected: 9 rows avg kW values, one for each Inverter device 
--           and one for the Metering device
-- Run     : source db/queries/1_3_midday_avg.sql
-- =============================================================

WITH midday AS (                      -- define it
  SELECT device, value AS kw
  FROM v_tlm
  WHERE point = 'AC_P_KW'
    AND ts >= '2026-10-09 15:00' AND ts < '2026-10-09 21:00'
)
SELECT device, AVG(kw) AS avg_kw      -- use it like a table
FROM midday
GROUP BY device;