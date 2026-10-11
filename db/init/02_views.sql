CREATE VIEW v_tlm AS
SELECT d.code AS device, d.device_type, p.name AS point,
       t.point_id, t.ts, t.value, t.quality
FROM telemetry t
JOIN point  p USING (point_id)
JOIN device d USING (device_id);