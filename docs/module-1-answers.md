# Module 1 - Answers

## 1.1 Environment
Default storage engine: InnoDB
Version: 12.3.3-MariaDB-ubu2404
Compile Machine: x86_64
Compile OS: debian-linux-gnu

## 1.2 Load and Explore
Inverter with fewer samples, and why: SPS01_B01_INV02 has 20 fewer samples.
 MariaDB [plant]> source db/queries/1_2_sample_count.sql
+-----------------+-------------+---------+
| device          | point       | samples |
+-----------------+-------------+---------+
| SPS01_B01_INV02 | AC_P_KW     |    1420 |
| SPS01_B01_INV02 | DC_P_KW     |    1420 |
| SPS01_B01_INV02 | TEMP_C      |    1420 |
| SPS01_B01_INV01 | AC_P_KW     |    1440 |
| SPS01_B01_INV01 | DC_P_KW     |    1440 |
| SPS01_B01_INV01 | TEMP_C      |    1440 |
| SPS01_B01_INV03 | AC_P_KW     |    1440 |
| SPS01_B01_INV03 | DC_P_KW     |    1440 |
| SPS01_B01_INV03 | TEMP_C      |    1440 |
| SPS01_B01_INV04 | AC_P_KW     |    1440 |
| SPS01_B01_INV04 | DC_P_KW     |    1440 |
| SPS01_B01_INV04 | TEMP_C      |    1440 |
| SPS01_B02_INV01 | AC_P_KW     |    1440 |
| SPS01_B02_INV01 | DC_P_KW     |    1440 |
| SPS01_B02_INV01 | TEMP_C      |    1440 |
| SPS01_B02_INV02 | AC_P_KW     |    1440 |
| SPS01_B02_INV02 | DC_P_KW     |    1440 |
| SPS01_B02_INV02 | TEMP_C      |    1440 |
| SPS01_B02_INV03 | AC_P_KW     |    1440 |
| SPS01_B02_INV03 | DC_P_KW     |    1440 |
| SPS01_B02_INV03 | TEMP_C      |    1440 |
| SPS01_B02_INV04 | AC_P_KW     |    1440 |
| SPS01_B02_INV04 | DC_P_KW     |    1440 |
| SPS01_B02_INV04 | TEMP_C      |    1440 |
| SPS01_MET01     | AMB_TEMP_C  |    1440 |
| SPS01_MET01     | POA_IRR_WM2 |    1440 |
| SPS01_MTR01     | AC_P_KW     |    1440 |
+-----------------+-------------+---------+
27 rows in set (0.024 sec)

When looking at the time series for SPS01_B01_INV02 there is a data gap 
from 2026-10-09 17:00:00.000 to 2026-10-09 17:19:00.000

MariaDB [plant]> source db/queries/1_2_missing_minutes_seq_engine.sql
+---------------------+
| missing_minute      |
+---------------------+
| 2026-10-09 17:00:00 |
| 2026-10-09 17:01:00 |
| 2026-10-09 17:02:00 |
| 2026-10-09 17:03:00 |
| 2026-10-09 17:04:00 |
| 2026-10-09 17:05:00 |
| 2026-10-09 17:06:00 |
| 2026-10-09 17:07:00 |
| 2026-10-09 17:08:00 |
| 2026-10-09 17:09:00 |
| 2026-10-09 17:10:00 |
| 2026-10-09 17:11:00 |
| 2026-10-09 17:12:00 |
| 2026-10-09 17:13:00 |
| 2026-10-09 17:14:00 |
| 2026-10-09 17:15:00 |
| 2026-10-09 17:16:00 |
| 2026-10-09 17:17:00 |
| 2026-10-09 17:18:00 |
| 2026-10-09 17:19:00 |
+---------------------+
20 rows in set (0.004 sec)

## 1.3 Find the planted faults
Underperforming inverter: SPS01_B02_INV03

Comms gap for SPS01_B01_INV02:
  Start: 2026-10-09 17:00:00
  End: 2026-10-09 17:19:00
  Duration: 20 minutes

1. Using underperformers.sql we find that the avg_ratio for SPS01_B02_INV03 across all 
360 samples is 0.759. This points to a consistent shortfall (< 0.95). 
MariaDB [plant]> source db/queries/underperformers.sql
+-----------------+---------+-----------+
| device          | samples | avg_ratio |
+-----------------+---------+-----------+
| SPS01_B02_INV03 |     360 |     0.759 |
+-----------------+---------+-----------+
1 row in set (0.007 sec)

2. By running 1_3_midday_avg.sql we can see that SPS01_B02_INV03 has a low avg_kw value 
and by modifying 1_2_missing_minutes_seq_engine.sql to look at SPS01_B02_INV03 we see 
there are no missing minutes so we can rule out any affects of missing data. 
MariaDB [plant]> source db/queries/1_3_midday_avg.sql
+-----------------+--------------------+
| device          | avg_kw             |
+-----------------+--------------------+
| SPS01_B01_INV01 | 154.83899999999997 |
| SPS01_B01_INV02 | 153.57685294117653 |
| SPS01_B01_INV03 | 154.78980555555538 |
| SPS01_B01_INV04 | 154.75477777777778 |
| SPS01_B02_INV01 | 154.76611111111117 |
| SPS01_B02_INV02 |  154.8151666666668 |
| SPS01_B02_INV03 | 117.25402777777789 |
| SPS01_B02_INV04 | 154.65658333333334 |
| SPS01_MTR01     | 1182.6194166666667 |
+-----------------+--------------------+
9 rows in set (0.002 sec)
MariaDB [plant]> source db/queries/1_2_missing_minutes_seq_engine.sql
Empty set (0.002 sec)

3. Running a quick check of the average DC power (1_3_average_dc_kw.sql) we see 
SPS01_B02_INV03 is at 120.3 kW while all the other inverters run in the 
neighborhood of 157.5 - 158.8 kW.
MariaDB [plant]> source db/queries/1_3_average_dc_kw.sql
+-----------------+-----------+
| device          | avg_dc_kw |
+-----------------+-----------+
| SPS01_B02_INV03 |     120.3 |
| SPS01_B01_INV02 |     157.5 |
| SPS01_B02_INV04 |     158.6 |
| SPS01_B01_INV04 |     158.7 |
| SPS01_B02_INV01 |     158.7 |
| SPS01_B02_INV02 |     158.8 |
| SPS01_B01_INV01 |     158.8 |
| SPS01_B01_INV03 |     158.8 |
+-----------------+-----------+
8 rows in set (0.004 sec)

Given each of these points we can identify SPS01_B02_INV03 as the underperforming inverter.

Because the plant's DC capacity exceeds the inverters' AC rating (DC/AC ratio 1.3,
325 kW of panels per 250 kW inverter), the healthy inverters clip at midday and
throw away their excess power, while the faulty inverter's reduced DC input stays
below its rating, so it never clips and its AC output comes within about 5% of its
neighbors despite a 25% DC loss. The fault is therefore most visible in AC data in
the morning and evening when running lower than capacity, or at any hour by 
comparing DC power.

## 1.4 15-minute rollup
Created the 15 minute rollup table with 02_schema.sql
MariaDB [plant]> source db/init/02_schema.sql
Query OK, 0 rows affected (0.023 sec)

Query in 1_4_15-minute_rollup.sql insert 2589 samples nesting the select statement 
  in the Insert statement. Possible future mods noted in the comments.
MariaDB [plant]> source db/queries/1_4_15-minute_rollup.sql
Query OK, 2589 rows affected (0.074 sec)
Records: 2589  Duplicates: 0  Warnings: 0

Keeping n_samples records how many raw values went into each 15-minute average. 
Once raw data is purged, it is the only way to tell a complete bucket from one 
built on partial data (e.g. SPS01_B01_INV02 17:15 has 10 of 15 samples because 
of the comms gap, and its 17:00 bucket has no row at all). It lets reports flag
incomplete intervals and lets hourly rollups use correctly weighted averages.
MariaDB [plant]> select * from telemetry_15m where n_samples < 15;
+----------+-------------------------+-----------+-----------+-----------+-----------+
| point_id | ts_15m                  | avg_value | min_value | max_value | n_samples |
+----------+-------------------------+-----------+-----------+-----------+-----------+
|        4 | 2026-10-09 17:15:00.000 |   212.721 |    193.42 |    228.32 |        10 |
|        5 | 2026-10-09 17:15:00.000 |   218.175 |    198.38 |    234.17 |        10 |
|        6 | 2026-10-09 17:15:00.000 |      51.2 |      49.3 |      52.7 |        10 |
+----------+-------------------------+-----------+-----------+-----------+-----------+
3 rows in set (0.001 sec)
MariaDB [plant]> select * from point where point_id >= 4 and point_id <= 6;
+----------+-----------+---------+------+
| point_id | device_id | name    | unit |
+----------+-----------+---------+------+
|        4 |         2 | AC_P_KW | kW   |
|        5 |         2 | DC_P_KW | kW   |
|        6 |         2 | TEMP_C  | degC |
+----------+-----------+---------+------+
3 rows in set (0.001 sec)
MariaDB [plant]> select * from device where device_id = 2;
+-----------+---------+-------------+-----------------+----------+------------+----------------+
| device_id | site_id | device_type | code            | rated_kw | ip_addr    | modbus_unit_id |
+-----------+---------+-------------+-----------------+----------+------------+----------------+
|         2 |       1 | INV         | SPS01_B01_INV02 |    250.0 | 10.10.1.12 |              1 |
+-----------+---------+-------------+-----------------+----------+------------+----------------+
1 row in set (0.002 sec)

## 1.5 Performance Ratio
We find the performance ration for SPS01 by running 
1_5_performance_ratio.sql resulting in the following:
+----------+--------------+----------------+-------+
| e_ac_kwh | h_poa_kwh_m2 | dc_capacity_kw | pr    |
+----------+--------------+----------------+-------+
|   9389.2 |        3.917 |         2600.0 | 0.922 |
+----------+--------------+----------------+-------+
1 row in set (0.016 sec)

Where e_ac_kwh is the energy actually delivered over the day. The value of h_poa_kwh_m2 
is the number of hours of full solar energy that each square meter of the panel produced
during the day (reference yield). Because this is below the values expected for a clear 
day in Florida (5-6 hours), it suggest that the day was cloudy and clipping didn't occur.
The dc_capacity_kw is the rated plant size, and pr is the calculated performance ratio.

Ideal energy  = plant size × equivalent full-sun hours
              = 2,600 kW × 3.917 h
              = 10,184 kWh      ← what a perfect, lossless plant would deliver

PR            = actual ÷ ideal
              = 9,389.2 ÷ 10,184
              = 0.922

The 92.2% performance rating is unrealistic as a typical plant runs around 78%-85%. The
temperature values are not being used in any of the calculations thus far and they can 
produce the biggest losses in a real-time system (6-9% according to Claude). Other
potential loss factors include aging wiring, reflection/low-light, inverter losses, 
shading, and downtime to name a few. The comms gap should not affect the power delivered
since it is a data loss not power loss.

## 1.6 Ramp Rate
Running 1_6_num_violations.sql and 1_6_largest_1_min_change.sql we find that there is 
a cloud clearing event (because ramp_up, not ramp_down) and that because the 
ramp_pvt_cap_per_min is 12.02% it violates the "no more than 10% change" rule.

MariaDB [plant]> source db/queries/1_6_num_violations.sql
+------------+---------+-----------+
| violations | ramp_up | ramp_down |
+------------+---------+-----------+
|          1 |       1 |         0 |
+------------+---------+-----------+
1 row in set (0.003 sec)

MariaDB [plant]> source db/queries/1_6_largest_1_min_change.sql
+-------------------------+---------+--------+-----------------+----------------------+
| ts                      | from_kw | to_kw  | ramp_kw_per_min | ramp_pct_cap_per_min |
+-------------------------+---------+--------+-----------------+----------------------+
| 2026-10-09 15:44:00.000 |   793.6 | 1034.1 |           240.4 |                12.02 |
+-------------------------+---------+--------+-----------------+----------------------+
1 row in set (0.002 sec)

## 1.7 Setpoint Audit
Prior to making any changes the plant_setpoint a query to select all produces the following:
+---------+------------+-----------+------------+
| site_id | p_limit_kw | pf_target | updated_by |
+---------+------------+-----------+------------+
|       1 |     2000.0 |     1.000 | seed       |
+---------+------------+-----------+------------+
1 row in set (0.002 sec)
Following two changes to the p_limit_kw (the first to 1850.0 and the second to 1200.0) a 
simple select * shows:
+---------+------------+-----------+------------+
| site_id | p_limit_kw | pf_target | updated_by |
+---------+------------+-----------+------------+
|       1 |     1200.0 |     1.000 | seed       |
+---------+------------+-----------+------------+
1 row in set (0.000 sec)
while the following shows all points of change:
MariaDB [plant]> select site_id, p_limit_kw, pf_target, updated_by, row_start, row_end 
    -> from plant_setpoint FOR SYSTEM_TIME ALL
    -> order by ROW_START;
+---------+------------+-----------+------------+----------------------------+----------------------------+
| site_id | p_limit_kw | pf_target | updated_by | row_start                  | row_end                    |
+---------+------------+-----------+------------+----------------------------+----------------------------+
|       1 |     2000.0 |     1.000 | seed       | 2026-10-13 04:32:43.154672 | 2026-10-15 18:46:34.198502 |
|       1 |     1850.0 |     1.000 | seed       | 2026-10-15 18:46:34.198502 | 2026-10-15 18:47:56.861484 |
|       1 |     1200.0 |     1.000 | seed       | 2026-10-15 18:47:56.861484 | 2106-02-07 06:28:15.999999 |
+---------+------------+-----------+------------+----------------------------+----------------------------+
3 rows in set (0.001 sec)

## 1.8 Retention
Added a partition for Jan 2027 by splitting pmax.
MariaDB [plant]> alter table telemetry reorganize partition 
    -> pmax into (
    -> partition p2027_01 values less than ('2027-02-01'),
    -> partition pmax values less than (MAXVALUE));
Query OK, 0 rows affected (0.064 sec)
Records: 0  Duplicates: 0  Warnings: 0

Verifying that the new partition exists we can use explain either generally on telemetry or using ts bounds
MariaDB [plant]> explain partitions
    -> select * from telemetry;
+------+-------------+-----------+------------------------------------------+------+---------------+------+---------+------+-------+-------+
| id   | select_type | table     | partitions                               | type | possible_keys | key  | key_len | ref  | rows  | Extra |
+------+-------------+-----------+------------------------------------------+------+---------------+------+---------+------+-------+-------+
|    1 | SIMPLE      | telemetry | p2026_10,p2026_11,p2026_12,p2027_01,pmax | ALL  | NULL          | NULL | NULL    | NULL | 30274 |       |
+------+-------------+-----------+------------------------------------------+------+---------------+------+---------+------+-------+-------+
1 row in set (0.002 sec)

MariaDB [plant]> explain partitions select * from telemetry
    -> where ts > '2026-10-9' and ts < '2026-10-10';
+------+-------------+-----------+------------+------+---------------+------+---------+------+-------+-------------+
| id   | select_type | table     | partitions | type | possible_keys | key  | key_len | ref  | rows  | Extra       |
+------+-------------+-----------+------------+------+---------------+------+---------+------+-------+-------------+
|    1 | SIMPLE      | telemetry | p2026_10   | ALL  | NULL          | NULL | NULL    | NULL | 30270 | Using where |
+------+-------------+-----------+------------+------+---------------+------+---------+------+-------+-------------+
1 row in set (0.001 sec)

NOTED FOR FUTURE REFERENCE: Adding the partition has been captured in db/migrations/001_add_p2027_01.sql.