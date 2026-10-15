-- 15 minute rollup of telemetry data
CREATE TABLE telemetry_15m (
  point_id  INT UNSIGNED NOT NULL,
  ts_15m    DATETIME(3)  NOT NULL,                  -- always UTC
  avg_value DOUBLE,
  min_value DOUBLE,
  max_value DOUBLE,
  n_samples INT UNSIGNED,
  PRIMARY KEY (point_id, ts_15m)
);