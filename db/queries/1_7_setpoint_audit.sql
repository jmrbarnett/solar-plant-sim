-- Update the commanded setpoint for the site
--  This is just an example of the last update run manually during the exercise
UPDATE plant_setpoint SET p_limit_kw = 1850, updated_by = 'jbarnett' WHERE site_id = 1;