-- =================================================================================
-- Exercise 1.6: Count the violations both upward and downward
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
)
SELECT COUNT(*) as violations,
       SUM(d.ramp > 0) as ramp_up,
       SUM(d.ramp < 0) as ramp_down
FROM deltas d
CROSS JOIN plant p
WHERE 100 * ABS(d.ramp) / p.ac_capacity_kw > 10;