WITH r AS (
  SELECT device, ts, value AS kw,
         MEDIAN(value) OVER (PARTITION BY ts) AS fleet_median
  FROM v_tlm
  WHERE device_type = 'INV' AND point = 'AC_P_KW'
    AND ts >= '2026-10-09 15:00' AND ts < '2026-10-09 21:00'  -- midday, UTC
)
SELECT device,
       COUNT(*)                                  AS samples,
       ROUND(AVG(kw / NULLIF(fleet_median, 0)), 3) AS avg_ratio
FROM r
GROUP BY device
HAVING avg_ratio < 0.95;