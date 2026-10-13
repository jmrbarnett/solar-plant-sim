SELECT device, point, ts AS gap_start, next_ts AS gap_end,
       TIMESTAMPDIFF(SECOND, ts, next_ts) AS gap_s
FROM (
  SELECT v.*, LEAD(ts) OVER (PARTITION BY point_id ORDER BY ts) AS next_ts
  FROM v_tlm v
  WHERE ts >= '2026-10-09' AND ts < '2026-10-10'
) x
WHERE TIMESTAMPDIFF(SECOND, ts, next_ts) > 180;    -- expected interval 60 s