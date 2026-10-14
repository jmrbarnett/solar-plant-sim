-- Build a partitioned view of the latest telemetry values for each point, 
--  using a window function (MAX(ts)) to find the most recent timestamp per point_id. 
--  This is useful for quickly retrieving the latest readings from all devices 
--  and points without scanning the entire telemetry table.

SELECT device, point, ts, value
FROM (
    SELECT v.*, ROW_NUMBER() OVER (PARTITION BY point_id ORDER BY ts DESC) AS rn
    FROM v_tlm v
    WHERE ts >= (SELECT MAX(ts) FROM telemetry) - INTERVAL 1 HOUR
) x
WHERE rn = 1;