-- Legacy feedback tables from the earlier integration build (test fixture schema).

CREATE TABLE IF NOT EXISTS external_feedback (
	id SERIAL NOT NULL, 
	facility_id INTEGER, 
	facility_name VARCHAR(160) NOT NULL, 
	platform VARCHAR(30) NOT NULL, 
	external_id VARCHAR(128) NOT NULL, 
	source_url TEXT NOT NULL, 
	original_text TEXT NOT NULL, 
	classification VARCHAR(50) NOT NULL, 
	sentiment VARCHAR(30), 
	collected_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_external_feedback_source UNIQUE (platform, external_id), 
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE SET NULL
)

;

CREATE INDEX IF NOT EXISTS ix_external_feedback_facility_id ON external_feedback (facility_id);

CREATE INDEX IF NOT EXISTS ix_external_feedback_platform ON external_feedback (platform);

CREATE INDEX IF NOT EXISTS ix_external_feedback_facility_name ON external_feedback (facility_name);
CREATE TABLE IF NOT EXISTS external_google_ratings (review_id VARCHAR(255) PRIMARY KEY, place_id VARCHAR(255) NOT NULL, stars SMALLINT NOT NULL);
