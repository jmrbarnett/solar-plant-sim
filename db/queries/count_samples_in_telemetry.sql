-- Query to count the number of samples in the telemetry table for each device type,
--  along with the number of distinct devices of that type, for a specific date range.
SELECT d.device_type, COUNT(DISTINCT d.code) AS devices, COUNT(*) AS samples
FROM v_tlm v
JOIN device d ON d.code = v.device
WHERE v.ts >= '2026-10-10' AND v.ts < '2026-10-11'
GROUP BY d.device_type;
