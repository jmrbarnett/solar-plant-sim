# Module 1 - Answers

## 1.1 Environment
Default storage engine: InnoDB
Version: 12.3.3-MariaDB-ubu2404
Compile Machine: x86_64
Compile OS: debian-linux-gnu

## 1.2 Load and Explore
Inverter with fewer samples, and why: SPS01_B01_INV02 has 20 fewer samples. 
There is a data gap at 2026-10-09 17:00:00.000 to 2026-10-09 17:19:00.000

## 1.3 Find the planted faults
Underperforming inverter: SPS01_B02_INV03

Comms gap for SPS01_B01_INV02:
  Start: 2026-10-09 17:00:00
  End: 2026-10-09 17:19:00
  Duration: 20 minutes

1. Using underperformers.sql we find that the avg_ratio for SPS01_B02_INV03 across all 
360 samples is 0.759. This points to a consistent shortfall (< 0.95). 
2. By running 1_3_midday_avg.sql we can see that SPS01_B02_INV03 has a low avg_kw value 
and by modifying 1_2_missing_minutes_seq_engine.sql to look at SPS01_B02_INV03 we see 
there are no missing minutes so we can rule out any affects of missing data. 
3. Running a quick check of the average DC power (1_3_average_dc_kw.sql) we see 
SPS01_B02_INV03 is at 120.3 kW while all the other inverters run in the 
neighborhood of 157.5 - 158.8 kW.

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
Query in 1_4_15-minute_rollup.sql insert 2589 samples nesting the select statement 
  in the Insert statement. Possible future mods noted in the comments.
Keeping n_samples records how many raw values went into each 15-minute average. 
Once raw data is purged, it is the only way to tell a complete bucket from one 
built on partial data (e.g. SPS01_B01_INV02 17:15 has 10 of 15 samples because 
of the comms gap, and its 17:00 bucket has no row at all). It lets reports flag
incomplete intervals and lets hourly rollups use correctly weighted averages.