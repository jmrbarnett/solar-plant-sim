-- Convert the AC_P_KW telemetry readings from kW to kWh for each Inverter device
--  The trapezoidal rule approximates the area under the curve by averaging 
--  consecutive readings and multiplying by the time difference.
--    kWh for one interval = (kw + prev_kw) / 2  ×  hours between samples
--  The sum of all intervals gives the total energy produced by the device over the day.
-- 
--  This query uses the LAG() window function to access the previous timestamp and value
--  for each device, and filters out the first reading (which has no previous value).
--  Also utilizes CTE and Window functions to simplify the query and avoid self-joins.
-- 
--  This is useful for calculating the total energy produced by each inverter over a day.

WITH s AS ( -- Use a CTE to calculate the previous timestamp and value for each reading
  SELECT device, ts, value AS kw,
         LAG(ts)    OVER w AS prev_ts,
         LAG(value) OVER w AS prev_kw
  FROM v_tlm
  WHERE device_type = 'INV' AND point = 'AC_P_KW'
    AND ts >= '2026-10-09' AND ts < '2026-10-10'  -- Only consider readings from the specified day
  WINDOW w AS (PARTITION BY point_id ORDER BY ts) -- build a partitioned view of the telemetry data for speed
)
SELECT device,
       ROUND(SUM((kw + prev_kw) / 2
                 * TIMESTAMPDIFF(MICROSECOND, prev_ts, ts) / 3.6e9), 1) AS kwh  -- Calculate kWh and convert microseconds to hours
FROM s
WHERE prev_ts IS NOT NULL -- exclude the first reading for each device, which has no previous value
GROUP BY device
ORDER BY kwh;