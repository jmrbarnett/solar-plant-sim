-- Exercise 1.4: 15-minute rollup of telemetry data
--  Using the raw telemetry data, create a 15-minute rollup of the average, 
--  minimum, maximum, and number of samples for each point_id.
--
-- Currently this query is hard-coded to the date 2026-10-09, and when run multiple 
--  times will overwrite the previous results for that date.
-- To generalize this query, change the date in the WHERE clause OR modify the clause
--  to use a parameterized query and pass in the desired date(s) at runtime. 
--   (WHERE ts >= ? AND ts < ?)
-- Also if this is to be reused, to avoid the table growing too big, TRUNCATE the 
--  telemetry_15m table before running and remove the ON DUPLICATE KEY UPDATE clause, 
--  or change the INSERT to an INSERT IGNORE.

INSERT into telemetry_15m (point_id, ts_15m, avg_value, min_value, max_value, n_samples)
    SELECT point_id,
       FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(ts) / 900) * 900) AS ts_15m,
       AVG(value)  AS avg_value,
       MIN(value)  AS min_value,
       MAX(value)  AS max_value,
       COUNT(*)    AS n_samples
    FROM telemetry
    WHERE ts >= '2026-10-09' AND ts < '2026-10-10'
    GROUP BY point_id, ts_15m
ON DUPLICATE KEY UPDATE
  avg_value = VALUES(avg_value), min_value = VALUES(min_value),
  max_value = VALUES(max_value), n_samples = VALUES(n_samples);