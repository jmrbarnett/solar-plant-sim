-- =============================================================
-- Exercise 1.2: Load and explore
-- Purpose : Count samples to verify that the data was loaded correctly
-- Expected: 1 site; 27 points; 38820 telemetry rows (27 points * 1440 minutes)
-- Run     : source db/queries/1_2_row_counts.sql
-- =============================================================

select 
    (select count(*) from site) as sites, 
    (select count(*) from point) as points, 
    (select count(*) from telemetry) as telemetry_rows;