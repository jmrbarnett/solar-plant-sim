-- Add a new partition for January 2027
--  This was done directly at the prompt. SQL saved here for future reference
alter table telemetry reorganize partition 
    pmax into (
    partition p2027_01 values less than ('2027-02-01'),
    partition pmax values less than (MAXVALUE));