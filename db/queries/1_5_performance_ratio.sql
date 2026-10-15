-- Performance Ratio (PR) is a measure of the efficiency of a solar plant, 
--  defined as the ratio of actual energy output to the theoretical maximum 
--  energy output based on the plant's DC capacity and the amount of sunlight received.
-- 
--             E_AC
-- PR = ─────────────────────
--       P_DC × (H_POA / G_STC)
-- 
-- Where:
--  E_AC = total AC energy produced by the plant over the day (kWh)
--  P_DC = total DC capacity of the plant (kW)
--  H_POA = total plane-of-array insolation over the day (kWh/m²)
--  G_STC = standard test condition irradiance (1 kW/m²)
      
WITH samples AS (                         -- 1. meter power with the previous sample
  SELECT ts, value AS kw,
         LAG(ts)    OVER w AS prev_ts,
         LAG(value) OVER w AS prev_kw
  FROM v_tlm
  WHERE device = 'SPS01_MTR01' AND point = 'AC_P_KW'
    AND ts >= '2026-10-09' AND ts < '2026-10-10'
  WINDOW w AS (PARTITION BY point_id ORDER BY ts)
),
energy AS (                               -- 2. integrate to one row of kWh
  SELECT SUM((kw + prev_kw) / 2
             * TIMESTAMPDIFF(MICROSECOND, prev_ts, ts) / 3.6e9) AS e_ac_kwh
  FROM samples
  WHERE prev_ts IS NOT NULL
),
insolation AS (                           -- 3. sunlight on the panels, kWh/m2
  SELECT SUM(value) * 60 / 3600000 AS h_poa_kwh_m2
  FROM v_tlm
  WHERE device = 'SPS01_MET01' AND point = 'POA_IRR_WM2'
    AND ts >= '2026-10-09' AND ts < '2026-10-10'
),
plant AS (                                -- 4. DC nameplate, kW
  SELECT dc_capacity_kw FROM site WHERE code = 'SPS01'
)
SELECT ROUND(e.e_ac_kwh, 1)     AS e_ac_kwh,
       ROUND(i.h_poa_kwh_m2, 3) AS h_poa_kwh_m2,
       p.dc_capacity_kw,
       ROUND(e.e_ac_kwh / (p.dc_capacity_kw * i.h_poa_kwh_m2 / 1.0), 3) AS pr
FROM energy e, insolation i, plant p;