-- Exercise 1.3: Average DC Power (kW) per Inverter

SELECT device, ROUND(AVG(value), 1) AS avg_dc_kw
FROM v_tlm
WHERE device_type = 'INV' AND point = 'DC_P_KW'
  AND ts >= '2026-10-09 15:00' AND ts < '2026-10-09 21:00'
GROUP BY device
ORDER BY avg_dc_kw;