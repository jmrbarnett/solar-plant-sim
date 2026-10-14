-- =============================================================
-- Exercise 1.2: Load and explore
-- Purpose : Count samples per device/point to find missing data
-- Expected: 27 rows; SPS01_B01_INV02 shows 1,420 samples on all
--           three points (20-minute comms gap), all others 1,440
-- Run     : source db/queries/1_2_sample_count.sql
-- =============================================================

SELECT device, point, COUNT(*) AS samples
FROM v_tlm
GROUP BY device, point
ORDER BY samples, device, point;