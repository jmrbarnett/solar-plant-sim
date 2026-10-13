WITH s AS (
  SELECT device, ts, value AS kw,
         LAG(ts)    OVER w AS prev_ts,
         LAG(value) OVER w AS prev_kw
  FROM v_tlm
  WHERE device_type = 'INV' AND point = 'AC_P_KW'
    AND ts >= '2026-10-09' AND ts < '2026-10-10'
  WINDOW w AS (PARTITION BY point_id ORDER BY ts)
)
SELECT device,
       ROUND(SUM((kw + prev_kw) / 2
                 * TIMESTAMPDIFF(MICROSECOND, prev_ts, ts) / 3.6e9), 1) AS kwh
FROM s
WHERE prev_ts IS NOT NULL
GROUP BY device
ORDER BY kwh;