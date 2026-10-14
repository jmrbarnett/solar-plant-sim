-- =============================================================
-- Exercise 1.2: Load and explore
-- Purpose : Find the specific missing timestamps 
--         : Uses the recureive CTE as opposed to the internal sequence engine
--         : Requires that max_recursive_iterations is set to at least 1440 
--           (the number of minutes in a day) in the database configuration.
--           This can be done with set session max_recursive_iterations = 1440
--           or by changing the configuration file.
--         : Does not require knowing the faulty device/point in advance, 
--           but does use a known point_id
-- Expected: 20 rows of timestamps, 17:00 through 17:19
-- Run     : source db/queries/1_2_missing_minutes_recur_CTE.sql
-- =============================================================

WITH RECURSIVE minutes AS (
  SELECT CAST('2026-10-09 00:00:00' AS DATETIME) AS ts      -- anchor: first row
  UNION ALL
  SELECT ts + INTERVAL 1 MINUTE FROM minutes                -- recursive step
  WHERE ts < '2026-10-09 23:59:00'                          -- stop condition
)
SELECT m.ts AS missing_minute
FROM minutes m
LEFT JOIN telemetry t
  ON t.point_id = 5 AND t.ts = m.ts
WHERE t.ts IS NULL;