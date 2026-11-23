-- One pending appointment request per patient, facility and preferred date.
-- Before applying to an existing database, check for rows that would violate the index:
--   SELECT user_id, facility_id, preferred_date, count(*) FROM appointment_requests
--   WHERE status = 'requested' GROUP BY 1, 2, 3 HAVING count(*) > 1;
CREATE UNIQUE INDEX IF NOT EXISTS uq_appointments_pending_per_day
    ON appointment_requests (user_id, facility_id, preferred_date)
    WHERE status = 'requested';
