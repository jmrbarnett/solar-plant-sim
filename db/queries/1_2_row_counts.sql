select 
    (select count(*) from site) as sites, 
    (select count(*) from point) as points, 
    (select count(*) from telemetry) as telemetry_rows;