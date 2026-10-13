SELECT device, point, ts, value
FROM (
    SELECT v.*, ROW_NUMBER() OVER (PARTITION BY point_id ORDER BY ts DESC) AS rn
    FROM v_tlm v
    WHERE ts >= (SELECT MAX(ts) FROM telemetry) - INTERVAL 1 HOUR
) x
WHERE rn = 1;