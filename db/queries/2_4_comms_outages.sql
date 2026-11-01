-- Exercise 2.4: comms outages from COMM_ST alone
WITH s AS (                                   -- each sample with the previous one beside it
  SELECT device, ts, value,
         LAG(value) OVER (PARTITION BY point_id ORDER BY ts) AS prev
  FROM v_tlm
  WHERE point = 'COMM_ST'
    AND ts >= '2026-10-10' AND ts < '2026-10-11'    -- one day; keeps partition pruning
),
edges AS (                                    -- only the rows where the status changes
  SELECT device, ts, value
  FROM s
  WHERE prev IS NULL OR value <> prev
),
paired AS (                                   -- each change, plus when the next change happened
  SELECT device, value, ts AS outage_start,
         LEAD(ts) OVER (PARTITION BY device ORDER BY ts) AS outage_end
  FROM edges
)
SELECT device, outage_start, outage_end,
       TIMESTAMPDIFF(MINUTE, outage_start, outage_end) AS minutes
FROM paired
WHERE value = 0                               -- keep the changes to "down"
ORDER BY outage_start;