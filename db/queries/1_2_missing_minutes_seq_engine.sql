-- =============================================================
-- Exercise 1.2: Load and explore
-- Purpose : Find the specific missing timestamps for SPS01_B01_INV02/AC_P_KW
--         : Use the seq_0_to_1439 table to generate all minutes in a day
--         : Uses the internal sequence engine as opposed to a recursive CTE
--         : Does not require knowing the timeframe in advance,
--           but does require knowing the faulty device/point
-- Expected: 20 rows of timestamps, 17:00 through 17:19
-- Run     : source db/queries/1_2_missing_minutes_seq_engine.sql
-- =============================================================

SELECT '2026-10-09' + INTERVAL s.seq MINUTE AS missing_minute
FROM seq_0_to_1439 s
LEFT JOIN v_tlm t
  ON t.device = 'SPS01_B01_INV02'
 AND t.point  = 'AC_P_KW'
 AND t.ts     = '2026-10-09' + INTERVAL s.seq MINUTE
WHERE t.ts IS NULL;