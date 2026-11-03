-- =============================================================
-- Exercise 2.5: Tracker Controllers
-- Purpose : Find the specific stuck trackers from target-vs-actual error
--         : Does not require knowing the faulty device/point in advance, 
--           but filters by standard point names. Finds any stuck tracker
--           without knowing which in advance.
-- Expected: Stuck tracker on SPS01_B01_TRK03 from 18:00 to end of data
-- Run     : source db/queries/2_5_stuck_tracker.sql
-- =============================================================

WITH angles AS (                         -- one row per tracker per minute: target and actual side by side
  SELECT device, ts,
         MAX(CASE WHEN point = 'ANG_TGT_DEG' THEN value END) AS tgt,
         MAX(CASE WHEN point = 'ANG_ACT_DEG' THEN value END) AS act
  FROM v_tlm
  WHERE point IN ('ANG_TGT_DEG', 'ANG_ACT_DEG')
    AND ts >= '2026-10-10' AND ts < '2026-10-11'
  GROUP BY device, ts
)
SELECT device,
       MIN(ts)                         AS first_flagged,
       MAX(ts)                         AS last_flagged,
       COUNT(*)                        AS minutes_off,
       ROUND(MAX(ABS(tgt - act)), 1)   AS max_error_deg
FROM angles
WHERE ABS(tgt - act) > 5                 -- tolerance: well above normal positioning error
GROUP BY device
HAVING COUNT(*) >= 10                    -- sustained, not a momentary blip
ORDER BY minutes_off DESC;
