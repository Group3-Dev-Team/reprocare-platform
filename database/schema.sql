-- ReproCare PostgreSQL schema.
-- Generated from backend/app/models by `python -m app.database.export_schema`. Do not edit by hand.

CREATE TABLE articles (
	id SERIAL NOT NULL,
	slug VARCHAR(120) NOT NULL,
	title VARCHAR(200) NOT NULL,
	category VARCHAR(60) NOT NULL,
	summary TEXT NOT NULL,
	read_minutes INTEGER NOT NULL,
	sections JSON NOT NULL,
	questions_to_ask JSON NOT NULL,
	"references" JSON NOT NULL,
	related_services VARCHAR(255) NOT NULL,
	review_status VARCHAR(160) NOT NULL,
	updated_on DATE,
	PRIMARY KEY (id)
);

CREATE INDEX ix_articles_category ON articles (category);
CREATE UNIQUE INDEX ix_articles_slug ON articles (slug);

CREATE TABLE data_sources (
	id SERIAL NOT NULL,
	code VARCHAR(40) NOT NULL,
	name VARCHAR(120) NOT NULL,
	description TEXT NOT NULL,
	attribution VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (code)
);


CREATE TABLE insurers (
	id SERIAL NOT NULL,
	slug VARCHAR(60) NOT NULL,
	name VARCHAR(120) NOT NULL,
	kind VARCHAR(80) NOT NULL,
	note TEXT NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (slug)
);


CREATE TABLE services (
	id SERIAL NOT NULL,
	slug VARCHAR(60) NOT NULL,
	name VARCHAR(120) NOT NULL,
	short_description VARCHAR(160) NOT NULL,
	keywords TEXT NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (slug)
);


CREATE TABLE facilities (
	id SERIAL NOT NULL,
	slug VARCHAR(120) NOT NULL,
	name VARCHAR(160) NOT NULL,
	facility_type VARCHAR(30) NOT NULL,
	description TEXT NOT NULL,
	address VARCHAR(255) NOT NULL,
	area VARCHAR(120) NOT NULL,
	town VARCHAR(80) NOT NULL,
	county VARCHAR(80) NOT NULL,
	latitude FLOAT,
	longitude FLOAT,
	phone VARCHAR(40) NOT NULL,
	email VARCHAR(255) NOT NULL,
	website VARCHAR(255) NOT NULL,
	weekday_hours VARCHAR(60) NOT NULL,
	saturday_hours VARCHAR(60) NOT NULL,
	sunday_hours VARCHAR(60) NOT NULL,
	open_24_hours BOOLEAN NOT NULL,
	open_weekends BOOLEAN NOT NULL,
	languages VARCHAR(255) NOT NULL,
	payment_methods VARCHAR(255) NOT NULL,
	accessibility TEXT NOT NULL,
	offers_telehealth BOOLEAN NOT NULL,
	accepts_appointment_requests BOOLEAN NOT NULL,
	registration_status VARCHAR(20) NOT NULL,
	registration_body VARCHAR(160) NOT NULL,
	registration_code VARCHAR(60) NOT NULL,
	registration_checked_on DATE,
	image_key VARCHAR(40) NOT NULL,
	is_demo BOOLEAN NOT NULL,
	source_id INTEGER,
	external_id VARCHAR(160),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_facilities_type CHECK (facility_type IN ('hospital', 'clinic', 'maternity_home', 'health_centre', 'laboratory')),
	CONSTRAINT ck_facilities_registration_status CHECK (registration_status IN ('matched', 'not_checked', 'unresolved')),
	CONSTRAINT uq_facilities_source_external UNIQUE (source_id, external_id),
	FOREIGN KEY(source_id) REFERENCES data_sources (id) ON DELETE SET NULL
);

CREATE INDEX ix_facilities_county ON facilities (county);
CREATE INDEX ix_facilities_facility_type ON facilities (facility_type);
CREATE INDEX ix_facilities_is_demo ON facilities (is_demo);
CREATE INDEX ix_facilities_name ON facilities (name);
CREATE UNIQUE INDEX ix_facilities_slug ON facilities (slug);
CREATE INDEX ix_facilities_source_id ON facilities (source_id);
CREATE INDEX ix_facilities_town ON facilities (town);

CREATE TABLE community_programs (
	id SERIAL NOT NULL,
	slug VARCHAR(120) NOT NULL,
	title VARCHAR(160) NOT NULL,
	program_type VARCHAR(20) NOT NULL,
	summary VARCHAR(255) NOT NULL,
	description TEXT NOT NULL,
	organizer_name VARCHAR(160) NOT NULL,
	service_id INTEGER,
	host_facility_id INTEGER,
	venue VARCHAR(255) NOT NULL,
	town VARCHAR(80) NOT NULL,
	county VARCHAR(80) NOT NULL,
	latitude FLOAT,
	longitude FLOAT,
	start_date DATE NOT NULL,
	start_time VARCHAR(20) NOT NULL,
	end_time VARCHAR(20) NOT NULL,
	eligibility TEXT NOT NULL,
	requirements TEXT NOT NULL,
	cost_type VARCHAR(20) NOT NULL,
	cost_note VARCHAR(255) NOT NULL,
	capacity INTEGER NOT NULL,
	status VARCHAR(20) NOT NULL,
	is_demo BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_programs_type CHECK (program_type IN ('screening', 'testing', 'education', 'outreach')),
	CONSTRAINT ck_programs_cost CHECK (cost_type IN ('free', 'subsidised', 'paid')),
	CONSTRAINT ck_programs_status CHECK (status IN ('published', 'draft', 'cancelled')),
	CONSTRAINT ck_programs_capacity CHECK (capacity > 0),
	FOREIGN KEY(service_id) REFERENCES services (id) ON DELETE SET NULL,
	FOREIGN KEY(host_facility_id) REFERENCES facilities (id) ON DELETE SET NULL
);

CREATE INDEX ix_community_programs_cost_type ON community_programs (cost_type);
CREATE INDEX ix_community_programs_program_type ON community_programs (program_type);
CREATE INDEX ix_community_programs_service_id ON community_programs (service_id);
CREATE UNIQUE INDEX ix_community_programs_slug ON community_programs (slug);
CREATE INDEX ix_community_programs_start_date ON community_programs (start_date);
CREATE INDEX ix_community_programs_town ON community_programs (town);

CREATE TABLE external_collection_runs (
	id SERIAL NOT NULL,
	facility_id INTEGER,
	platform VARCHAR(20) NOT NULL,
	status VARCHAR(20) NOT NULL,
	message TEXT NOT NULL,
	posts_found INTEGER NOT NULL,
	comments_created INTEGER NOT NULL,
	comments_skipped INTEGER NOT NULL,
	started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE SET NULL
);

CREATE INDEX ix_external_collection_runs_facility_id ON external_collection_runs (facility_id);
CREATE INDEX ix_external_collection_runs_platform ON external_collection_runs (platform);

CREATE TABLE facility_external_profiles (
	id SERIAL NOT NULL,
	facility_id INTEGER NOT NULL,
	platform VARCHAR(20) NOT NULL,
	external_id VARCHAR(255) NOT NULL,
	url TEXT NOT NULL,
	display_name VARCHAR(255) NOT NULL,
	match_method VARCHAR(40) NOT NULL,
	rating FLOAT,
	rating_count INTEGER,
	photos JSON NOT NULL,
	details JSON NOT NULL,
	fetched_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_external_profiles_platform CHECK (platform IN ('facebook', 'tiktok', 'google')),
	CONSTRAINT uq_external_profiles_facility_platform_id UNIQUE (facility_id, platform, external_id),
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE CASCADE
);

CREATE INDEX ix_facility_external_profiles_facility_id ON facility_external_profiles (facility_id);
CREATE INDEX ix_facility_external_profiles_platform ON facility_external_profiles (platform);

CREATE TABLE facility_insurers (
	facility_id INTEGER NOT NULL,
	insurer_id INTEGER NOT NULL,
	PRIMARY KEY (facility_id, insurer_id),
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE CASCADE,
	FOREIGN KEY(insurer_id) REFERENCES insurers (id) ON DELETE CASCADE
);


CREATE TABLE facility_services (
	facility_id INTEGER NOT NULL,
	service_id INTEGER NOT NULL,
	PRIMARY KEY (facility_id, service_id),
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE CASCADE,
	FOREIGN KEY(service_id) REFERENCES services (id) ON DELETE CASCADE
);


CREATE TABLE lab_tests (
	id SERIAL NOT NULL,
	facility_id INTEGER NOT NULL,
	name VARCHAR(160) NOT NULL,
	sample_type VARCHAR(120) NOT NULL,
	turnaround VARCHAR(60) NOT NULL,
	price_note VARCHAR(80) NOT NULL,
	home_collection BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE CASCADE
);

CREATE INDEX ix_lab_tests_facility_id ON lab_tests (facility_id);

CREATE TABLE practitioners (
	id SERIAL NOT NULL,
	slug VARCHAR(120) NOT NULL,
	full_name VARCHAR(160) NOT NULL,
	title VARCHAR(120) NOT NULL,
	specialty VARCHAR(120) NOT NULL,
	town VARCHAR(80) NOT NULL,
	gender VARCHAR(20) NOT NULL,
	languages VARCHAR(255) NOT NULL,
	offers_telehealth BOOLEAN NOT NULL,
	bio TEXT NOT NULL,
	fee_note VARCHAR(160) NOT NULL,
	facility_id INTEGER,
	registration_status VARCHAR(20) NOT NULL,
	registration_body VARCHAR(120) NOT NULL,
	registration_code VARCHAR(60) NOT NULL,
	registration_checked_on DATE,
	is_demo BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_practitioners_registration_status CHECK (registration_status IN ('matched', 'not_checked', 'unresolved')),
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE SET NULL
);

CREATE INDEX ix_practitioners_facility_id ON practitioners (facility_id);
CREATE INDEX ix_practitioners_full_name ON practitioners (full_name);
CREATE UNIQUE INDEX ix_practitioners_slug ON practitioners (slug);
CREATE INDEX ix_practitioners_specialty ON practitioners (specialty);
CREATE INDEX ix_practitioners_town ON practitioners (town);

CREATE TABLE users (
	id SERIAL NOT NULL,
	email VARCHAR(255) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	full_name VARCHAR(120) NOT NULL,
	phone VARCHAR(40),
	role VARCHAR(20) NOT NULL,
	facility_id INTEGER,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_users_role CHECK (role IN ('patient', 'facility_staff', 'admin')),
	CONSTRAINT ck_users_staff_facility CHECK ((role = 'facility_staff') = (facility_id IS NOT NULL)),
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_facility_id ON users (facility_id);

CREATE TABLE appointment_requests (
	id SERIAL NOT NULL,
	reference VARCHAR(20) NOT NULL,
	user_id INTEGER NOT NULL,
	facility_id INTEGER NOT NULL,
	practitioner_id INTEGER,
	service_id INTEGER,
	preferred_date DATE NOT NULL,
	preferred_time VARCHAR(20) NOT NULL,
	contact_phone VARCHAR(40) NOT NULL,
	notes TEXT NOT NULL,
	status VARCHAR(20) NOT NULL,
	facility_note TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_appointments_status CHECK (status IN ('requested', 'confirmed', 'declined', 'cancelled')),
	CONSTRAINT ck_appointments_time CHECK (preferred_time IN ('morning', 'afternoon', 'evening')),
	UNIQUE (reference),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE CASCADE,
	FOREIGN KEY(practitioner_id) REFERENCES practitioners (id) ON DELETE SET NULL,
	FOREIGN KEY(service_id) REFERENCES services (id) ON DELETE SET NULL
);

CREATE INDEX ix_appointment_requests_facility_id ON appointment_requests (facility_id);
CREATE INDEX ix_appointment_requests_status ON appointment_requests (status);
CREATE INDEX ix_appointment_requests_user_id ON appointment_requests (user_id);

CREATE TABLE contact_messages (
	id SERIAL NOT NULL,
	reference VARCHAR(20) NOT NULL,
	user_id INTEGER,
	name VARCHAR(120) NOT NULL,
	email VARCHAR(255) NOT NULL,
	topic VARCHAR(30) NOT NULL,
	message TEXT NOT NULL,
	status VARCHAR(20) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_contact_status CHECK (status IN ('new', 'in_progress', 'resolved')),
	CONSTRAINT ck_contact_topic CHECK (topic IN ('general', 'listing_correction', 'privacy', 'technical', 'feedback')),
	UNIQUE (reference),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_contact_messages_status ON contact_messages (status);

CREATE TABLE external_posts (
	id SERIAL NOT NULL,
	facility_id INTEGER,
	platform VARCHAR(20) NOT NULL,
	external_id VARCHAR(255) NOT NULL,
	url TEXT NOT NULL,
	author_name VARCHAR(255) NOT NULL,
	caption TEXT NOT NULL,
	thumbnail_url TEXT NOT NULL,
	published_at TIMESTAMP WITH TIME ZONE,
	collected_at TIMESTAMP WITH TIME ZONE,
	match_method VARCHAR(40) NOT NULL,
	is_visible BOOLEAN NOT NULL,
	facebook_scope VARCHAR(20),
	facebook_reviewed_at TIMESTAMP WITH TIME ZONE,
	facebook_reviewed_by INTEGER,
	facebook_review_note TEXT,
	legacy_facility_name VARCHAR(160) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_external_posts_platform CHECK (platform IN ('facebook', 'tiktok', 'google')),
	CONSTRAINT uq_external_posts_platform_id UNIQUE (platform, external_id),
	CONSTRAINT ck_external_posts_facebook_scope CHECK (facebook_scope IS NULL OR (platform = 'facebook' AND facebook_scope IN ('facility', 'organization'))),
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE SET NULL,
	FOREIGN KEY(facebook_reviewed_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_external_posts_facility_id ON external_posts (facility_id);
CREATE INDEX ix_external_posts_platform ON external_posts (platform);

CREATE TABLE import_batches (
	id SERIAL NOT NULL,
	source_id INTEGER NOT NULL,
	submitted_by_user_id INTEGER,
	received_count INTEGER NOT NULL,
	created_count INTEGER NOT NULL,
	updated_count INTEGER NOT NULL,
	error_count INTEGER NOT NULL,
	errors JSON NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(source_id) REFERENCES data_sources (id) ON DELETE CASCADE,
	FOREIGN KEY(submitted_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_import_batches_source_id ON import_batches (source_id);

CREATE TABLE notifications (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	title VARCHAR(160) NOT NULL,
	body TEXT NOT NULL,
	link VARCHAR(255),
	is_read BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_notifications_user_id ON notifications (user_id);

CREATE TABLE program_registrations (
	id SERIAL NOT NULL,
	reference VARCHAR(20) NOT NULL,
	program_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	full_name VARCHAR(120) NOT NULL,
	phone VARCHAR(40) NOT NULL,
	status VARCHAR(20) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_registrations_program_user UNIQUE (program_id, user_id),
	CONSTRAINT ck_registrations_status CHECK (status IN ('registered', 'cancelled', 'attended')),
	UNIQUE (reference),
	FOREIGN KEY(program_id) REFERENCES community_programs (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_program_registrations_program_id ON program_registrations (program_id);
CREATE INDEX ix_program_registrations_user_id ON program_registrations (user_id);

CREATE TABLE reviews (
	id SERIAL NOT NULL,
	facility_id INTEGER NOT NULL,
	user_id INTEGER,
	service_id INTEGER,
	author_name VARCHAR(80) NOT NULL,
	rating INTEGER NOT NULL,
	title VARCHAR(160) NOT NULL,
	body TEXT NOT NULL,
	visit_month DATE,
	status VARCHAR(20) NOT NULL,
	moderation_note TEXT NOT NULL,
	facility_reply TEXT NOT NULL,
	is_demo BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_reviews_rating CHECK (rating BETWEEN 1 AND 5),
	CONSTRAINT ck_reviews_status CHECK (status IN ('pending', 'published', 'rejected')),
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(service_id) REFERENCES services (id) ON DELETE SET NULL
);

CREATE INDEX ix_reviews_facility_id ON reviews (facility_id);
CREATE INDEX ix_reviews_status ON reviews (status);
CREATE INDEX ix_reviews_user_id ON reviews (user_id);

CREATE TABLE saved_facilities (
	user_id INTEGER NOT NULL,
	facility_id INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (user_id, facility_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE CASCADE
);


CREATE TABLE user_sessions (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	token_hash VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	UNIQUE (token_hash)
);

CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);

CREATE TABLE external_comments (
	id SERIAL NOT NULL,
	post_id INTEGER NOT NULL,
	facility_id INTEGER,
	parent_id INTEGER,
	platform VARCHAR(20) NOT NULL,
	external_id VARCHAR(255) NOT NULL,
	author_name VARCHAR(255) NOT NULL,
	author_is_facility BOOLEAN NOT NULL,
	text TEXT NOT NULL,
	published_at TIMESTAMP WITH TIME ZONE,
	published_at_approximate BOOLEAN NOT NULL,
	collected_at TIMESTAMP WITH TIME ZONE,
	like_count INTEGER,
	source_rating INTEGER,
	status VARCHAR(20) NOT NULL,
	screening VARCHAR(40) NOT NULL,
	screening_reasons JSON NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_external_comments_platform CHECK (platform IN ('facebook', 'tiktok', 'google')),
	CONSTRAINT ck_external_comments_status CHECK (status IN ('visible', 'held', 'hidden')),
	CONSTRAINT ck_external_comments_rating CHECK (source_rating IS NULL OR source_rating BETWEEN 1 AND 5),
	CONSTRAINT uq_external_comments_platform_id UNIQUE (platform, external_id),
	FOREIGN KEY(post_id) REFERENCES external_posts (id) ON DELETE CASCADE,
	FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE SET NULL,
	FOREIGN KEY(parent_id) REFERENCES external_comments (id) ON DELETE CASCADE
);

CREATE INDEX ix_external_comments_facility_id ON external_comments (facility_id);
CREATE INDEX ix_external_comments_parent_id ON external_comments (parent_id);
CREATE INDEX ix_external_comments_platform ON external_comments (platform);
CREATE INDEX ix_external_comments_post_id ON external_comments (post_id);
CREATE INDEX ix_external_comments_status ON external_comments (status);
