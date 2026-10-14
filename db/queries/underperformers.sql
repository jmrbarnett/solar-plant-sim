-- Identify underperforming Inverters by using a Common Window Expression (CTE) and 
--  window functions to compute the median AC_P_KW across all Inverters at each ts, 
--  computing the ratio of each inverter's reading to the fleet median, and finally 
--  averaging those ratios over the time window. Any inverter with an average ratio 
--  below 0.95 is considered underperforming.

WITH r AS (
  SELECT device, ts, value AS kw,
         MEDIAN(value) OVER (PARTITION BY ts) AS fleet_median -- median will mitigate the effect of outliers
  FROM v_tlm
  WHERE device_type = 'INV' AND point = 'AC_P_KW'
    AND ts >= '2026-10-09 15:00' AND ts < '2026-10-09 21:00'  -- midday, UTC
)
SELECT device,
       COUNT(*)                                  AS samples,
       ROUND(AVG(kw / NULLIF(fleet_median, 0)), 3) AS avg_ratio -- NULLIF prevents division by zero
FROM r
GROUP BY device
HAVING avg_ratio < 0.95;  -- Filter after aggregating rows (HAVING)