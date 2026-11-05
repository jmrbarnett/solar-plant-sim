-- Using a window function over the telemetry data to
--  identify gaps in the readings for each point.
--  Flags any gaps over 3 minutes (180 seconds) as a potential data gap.

SELECT device, point, ts AS gap_start, next_ts AS gap_end,
       TIMESTAMPDIFF(SECOND, ts, next_ts) AS gap_s
FROM (
  SELECT v.*, LEAD(ts) OVER (PARTITION BY point_id ORDER BY ts) AS next_ts
  FROM v_tlm v
  WHERE ts >= '2026-10-10' AND ts < '2026-10-11'
) x
WHERE TIMESTAMPDIFF(SECOND, ts, next_ts) > 180    -- expected interval 60 s
ORDER BY device, gap_start;
