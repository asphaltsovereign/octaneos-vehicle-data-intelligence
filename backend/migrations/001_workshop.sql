BEGIN;
CREATE SCHEMA IF NOT EXISTS sentinel;
REVOKE ALL ON SCHEMA sentinel FROM PUBLIC;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='sentinel_app') THEN
  CREATE ROLE sentinel_app NOLOGIN NOSUPERUSER NOBYPASSRLS;
 END IF;
END $$;
GRANT USAGE ON SCHEMA sentinel TO sentinel_app;
CREATE TABLE sentinel.schema_migrations(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE FUNCTION sentinel.user_id() RETURNS uuid LANGUAGE sql STABLE AS $$
 SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid
$$;
CREATE TABLE sentinel.workshops(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),name text NOT NULL CHECK(length(name) BETWEEN 1 AND 120),created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE sentinel.memberships(workshop_id uuid NOT NULL REFERENCES sentinel.workshops(id),user_id uuid NOT NULL,role text NOT NULL DEFAULT 'owner' CHECK(role IN ('owner','technician')),PRIMARY KEY(workshop_id,user_id));
ALTER TABLE sentinel.memberships ENABLE ROW LEVEL SECURITY;
CREATE POLICY own_membership ON sentinel.memberships FOR SELECT TO sentinel_app USING(user_id=sentinel.user_id());
GRANT SELECT ON sentinel.memberships TO sentinel_app;
CREATE FUNCTION sentinel.is_member(w uuid) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT EXISTS(SELECT 1 FROM sentinel.memberships WHERE workshop_id=w AND user_id=sentinel.user_id())
$$;
ALTER TABLE sentinel.workshops ENABLE ROW LEVEL SECURITY;
CREATE POLICY member_workshops ON sentinel.workshops FOR SELECT TO sentinel_app USING(sentinel.is_member(id));
GRANT SELECT ON sentinel.workshops TO sentinel_app;
CREATE FUNCTION sentinel.create_workshop(n text) RETURNS sentinel.workshops LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,sentinel AS $$
DECLARE w sentinel.workshops;
BEGIN
 IF sentinel.user_id() IS NULL THEN RAISE EXCEPTION 'Authentication required'; END IF;
 IF (SELECT count(*) FROM sentinel.memberships WHERE user_id=sentinel.user_id()) >= 5 THEN RAISE EXCEPTION 'Workshop limit reached'; END IF;
 INSERT INTO sentinel.workshops(name) VALUES(n) RETURNING * INTO w;
 INSERT INTO sentinel.memberships(workshop_id,user_id) VALUES(w.id,sentinel.user_id());
 RETURN w;
END $$;
REVOKE ALL ON FUNCTION sentinel.create_workshop(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION sentinel.create_workshop(text) TO sentinel_app;
CREATE TABLE sentinel.customers(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),workshop_id uuid NOT NULL REFERENCES sentinel.workshops(id),name text NOT NULL CHECK(length(name) BETWEEN 1 AND 120),phone text NOT NULL DEFAULT '',notes text NOT NULL DEFAULT '',created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(workshop_id,id));
CREATE TABLE sentinel.vehicles(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),workshop_id uuid NOT NULL REFERENCES sentinel.workshops(id),customer_id uuid NOT NULL,make text NOT NULL,model text NOT NULL,year integer NOT NULL CHECK(year BETWEEN 1900 AND 2100),odometer integer NOT NULL CHECK(odometer>=0),registration text NOT NULL DEFAULT '',source_identifier text NOT NULL DEFAULT '',is_demo boolean NOT NULL DEFAULT false,created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(workshop_id,id),UNIQUE(workshop_id,customer_id,id),FOREIGN KEY(workshop_id,customer_id) REFERENCES sentinel.customers(workshop_id,id));
CREATE TABLE sentinel.jobs(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),workshop_id uuid NOT NULL REFERENCES sentinel.workshops(id),customer_id uuid NOT NULL,vehicle_id uuid NOT NULL,complaint text NOT NULL,observations text NOT NULL DEFAULT '',inspection jsonb NOT NULL DEFAULT '{}',status text NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','in_progress','reviewed','closed')),idempotency_key uuid NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now(),UNIQUE(workshop_id,id),UNIQUE(workshop_id,id,vehicle_id),UNIQUE(workshop_id,idempotency_key),FOREIGN KEY(workshop_id,customer_id,vehicle_id) REFERENCES sentinel.vehicles(workshop_id,customer_id,id));
CREATE TABLE sentinel.reports(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),workshop_id uuid NOT NULL REFERENCES sentinel.workshops(id),job_id uuid NOT NULL,vehicle_id uuid NOT NULL,source_classification text NOT NULL CHECK(source_classification IN ('manual','public_dataset','synthetic','vehicle_telemetry')),evidence jsonb NOT NULL,idempotency_key uuid NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(workshop_id,id),UNIQUE(workshop_id,id,job_id,vehicle_id),UNIQUE(workshop_id,job_id,idempotency_key),FOREIGN KEY(workshop_id,job_id,vehicle_id) REFERENCES sentinel.jobs(workshop_id,id,vehicle_id));
CREATE TABLE sentinel.report_reviews(report_id uuid PRIMARY KEY,workshop_id uuid NOT NULL,notes text NOT NULL DEFAULT '',reviewed_by uuid NOT NULL,updated_at timestamptz NOT NULL DEFAULT now(),FOREIGN KEY(workshop_id,report_id) REFERENCES sentinel.reports(workshop_id,id));
CREATE TABLE sentinel.passport_events(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),workshop_id uuid NOT NULL,report_id uuid NOT NULL,job_id uuid NOT NULL,vehicle_id uuid NOT NULL,source_classification text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(report_id),FOREIGN KEY(workshop_id,report_id,job_id,vehicle_id) REFERENCES sentinel.reports(workshop_id,id,job_id,vehicle_id));
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['customers','vehicles','jobs','reports','report_reviews','passport_events'] LOOP
  EXECUTE format('ALTER TABLE sentinel.%I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY member_access ON sentinel.%I TO sentinel_app USING (sentinel.is_member(workshop_id)) WITH CHECK (sentinel.is_member(workshop_id))',t);
 END LOOP;
END $$;
GRANT SELECT,INSERT,UPDATE,DELETE ON sentinel.customers,sentinel.vehicles,sentinel.jobs TO sentinel_app;
GRANT SELECT,INSERT ON sentinel.reports,sentinel.passport_events TO sentinel_app;
GRANT SELECT,INSERT,UPDATE ON sentinel.report_reviews TO sentinel_app;
GRANT SELECT ON sentinel.schema_migrations TO sentinel_app;
CREATE INDEX ON sentinel.jobs(workshop_id,created_at DESC);
CREATE INDEX ON sentinel.vehicles(workshop_id,customer_id);
CREATE INDEX ON sentinel.reports(workshop_id,job_id);
CREATE INDEX ON sentinel.passport_events(workshop_id,vehicle_id);
INSERT INTO sentinel.schema_migrations(version) VALUES('001_workshop');
COMMIT;
