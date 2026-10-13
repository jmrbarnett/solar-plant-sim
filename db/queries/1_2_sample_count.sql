SELECT device, point, COUNT(*) AS samples
FROM v_tlm
GROUP BY device, point
ORDER BY samples, device, point;