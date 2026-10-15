-- =================================================================================
-- Exercise 1.6: Ramp Rate - Determine the ramp rate for each minute time interval
--   and calculate the change in AC as a percentage of the AC capacity for the site.
--   Look at the largest value and determine if that exceeds the ramp cap agreement.
-- =================================================================================

WITH samples AS (                         -- 1. meter power with the previous sample
  SELECT ts, value AS kw,
         LAG(ts)    OVER w AS prev_ts,
         LAG(value) OVER w AS prev_kw
  FROM v_tlm
  WHERE device = 'SPS01_MTR01' AND point = 'AC_P_KW'
    AND ts >= '2026-10-09' AND ts < '2026-10-10'
  WINDOW w AS (PARTITION BY point_id ORDER BY ts)
),
plant AS (                                -- 2. AC nameplate, kW
  SELECT ac_capacity_kw FROM site WHERE code = 'SPS01'
),
deltas AS (                              -- 3. compute ramp in kW/min
  SELECT ts, kw, prev_kw,
         (kw - prev_kw) / (TIMESTAMPDIFF(SECOND, prev_ts, ts) / 60) AS ramp
  FROM samples
  WHERE prev_ts IS NOT NULL
)                                   -- 4. Now compute the 1-minute change in AC power
SELECT d.ts,                                -- timestamp of the second sample
    ROUND(d.prev_kw, 1) AS from_kw,         -- AC power at the first sample
    ROUND(d.kw, 1) AS to_kw,                -- AC power at the second sample
    ROUND(d.ramp, 1) AS ramp_kw_per_min,    -- change in AC power per minute
    ROUND(100 * ABS(d.ramp) / p.ac_capacity_kw, 2) AS ramp_pct_cap_per_min
FROM deltas d
CROSS JOIN plant p
ORDER BY ramp_pct_cap_per_min DESC
LIMIT 1;