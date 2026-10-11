CREATE TABLE site (
  site_id        SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  code           VARCHAR(16)  NOT NULL UNIQUE,      -- e.g. 'SPS01'
  name           VARCHAR(80)  NOT NULL,
  latitude       DECIMAL(8,5),
  longitude      DECIMAL(8,5),
  ac_capacity_kw DECIMAL(10,1) NOT NULL,
  dc_capacity_kw DECIMAL(10,1) NOT NULL,
  timezone       VARCHAR(40)  NOT NULL DEFAULT 'America/New_York'
);

CREATE TABLE device (
  device_id      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  site_id        SMALLINT UNSIGNED NOT NULL,
  device_type    ENUM('INV','MTR','MET','TRK') NOT NULL,
  code           VARCHAR(32)  NOT NULL UNIQUE,      -- e.g. 'SPS01_B01_INV03'
  rated_kw       DECIMAL(8,1),
  ip_addr        INET4,
  modbus_unit_id TINYINT UNSIGNED,
  FOREIGN KEY (site_id) REFERENCES site(site_id)
);

CREATE TABLE point (
  point_id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  device_id  INT UNSIGNED NOT NULL,
  name       VARCHAR(32)  NOT NULL,                 -- e.g. 'AC_P_KW'
  unit       VARCHAR(16),
  UNIQUE KEY (device_id, name),
  FOREIGN KEY (device_id) REFERENCES device(device_id)
);

-- Raw telemetry: narrow, partitioned by month, UTC timestamps
CREATE TABLE telemetry (
  point_id  INT UNSIGNED NOT NULL,
  ts        DATETIME(3)  NOT NULL,                  -- always UTC
  value     DOUBLE,
  quality   TINYINT UNSIGNED NOT NULL DEFAULT 192,  -- 192 = OPC 'Good'
  PRIMARY KEY (point_id, ts)
)
PARTITION BY RANGE COLUMNS (ts) (
  PARTITION p2026_10 VALUES LESS THAN ('2026-11-01'),
  PARTITION p2026_11 VALUES LESS THAN ('2026-12-01'),
  PARTITION p2026_12 VALUES LESS THAN ('2027-01-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);

-- Operator setpoints with automatic history
CREATE TABLE plant_setpoint (
  site_id     SMALLINT UNSIGNED PRIMARY KEY,
  p_limit_kw  DECIMAL(10,1) NOT NULL,
  pf_target   DECIMAL(4,3)  NOT NULL DEFAULT 1.000,
  updated_by  VARCHAR(32)
) WITH SYSTEM VERSIONING;