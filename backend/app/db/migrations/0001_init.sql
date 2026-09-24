-- ONEGOV / SETU — initial schema
-- Run against a Supabase Postgres project (uses auth.users + auth.uid()).
-- Citizen-owned tables are protected with RLS; official access is scoped
-- via the `officials` table (role + district).

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------

create type document_status as enum ('verified', 'pending', 'expired', 'action_needed');
create type application_step_status as enum (
  'not_started', 'blocked', 'in_progress', 'verified', 'ready', 'rejected'
);
create type sla_status as enum ('on_track', 'at_risk', 'breached');
create type consent_status as enum ('granted', 'revoked', 'expired');
create type official_role as enum ('department_officer', 'district_admin', 'super_admin');

-- ---------------------------------------------------------------------
-- Core citizen identity + profile
-- ---------------------------------------------------------------------

create table citizens (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null,
  dob date,
  district text,
  taluka text,
  phone text,
  email text,
  preferred_language text not null default 'en',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table profiles (
  citizen_id uuid primary key references citizens(id) on delete cascade,
  profile_completeness_pct int not null default 0,
  verified_attributes jsonb not null default '{}'::jsonb,
  -- linked identifiers are stored as opaque references only, never raw
  -- Aadhaar/identity numbers (see security.md: no real identifiers).
  linked_identifiers_redacted jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Document vault
-- ---------------------------------------------------------------------

create table documents (
  id uuid primary key default gen_random_uuid(),
  citizen_id uuid not null references citizens(id) on delete cascade,
  doc_type text not null,
  issuer text,
  appwrite_file_id text,
  status document_status not null default 'pending',
  expiry_date date,
  checksum text,
  source text not null default 'citizen_upload',
  last_verified_at timestamptz,
  created_at timestamptz not null default now()
);

create table document_verifications (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  verified_by text not null,
  verification_status document_status not null,
  notes text,
  verified_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Service / life-event catalog
-- ---------------------------------------------------------------------

create table services (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  department text not null,
  sla_days int not null default 7,
  description text
);

create table life_events (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  title_en text not null,
  title_mr text,
  title_hi text,
  description text
);

create table service_dependencies (
  id uuid primary key default gen_random_uuid(),
  life_event_id uuid not null references life_events(id) on delete cascade,
  service_id uuid not null references services(id) on delete cascade,
  depends_on_service_id uuid references services(id) on delete set null,
  sequence_order int not null default 0
);

-- ---------------------------------------------------------------------
-- Journeys (applications)
-- ---------------------------------------------------------------------

create table applications (
  id uuid primary key default gen_random_uuid(),
  citizen_id uuid not null references citizens(id) on delete cascade,
  life_event_id uuid not null references life_events(id),
  status text not null default 'active',
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create table application_steps (
  id uuid primary key default gen_random_uuid(),
  application_id uuid not null references applications(id) on delete cascade,
  service_id uuid not null references services(id),
  status application_step_status not null default 'not_started',
  blocked_reason text,
  started_at timestamptz,
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Consent
-- ---------------------------------------------------------------------

create table consents (
  id uuid primary key default gen_random_uuid(),
  citizen_id uuid not null references citizens(id) on delete cascade,
  application_id uuid references applications(id) on delete cascade,
  shared_attributes jsonb not null default '[]'::jsonb,
  recipient_department text not null,
  purpose text not null,
  status consent_status not null default 'granted',
  granted_at timestamptz not null default now(),
  expires_at timestamptz not null,
  revoked_at timestamptz
);

-- ---------------------------------------------------------------------
-- Connector hub (mock government departments)
-- ---------------------------------------------------------------------

create table connector_requests (
  id uuid primary key default gen_random_uuid(),
  application_step_id uuid not null references application_steps(id) on delete cascade,
  department text not null,
  service_code text not null,
  external_reference text,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'submitted',
  sla_due_at timestamptz,
  submitted_at timestamptz not null default now()
);

create table connector_events (
  id uuid primary key default gen_random_uuid(),
  connector_request_id uuid not null references connector_requests(id) on delete cascade,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  received_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- SLA / audit / notifications / analytics
-- ---------------------------------------------------------------------

create table sla_records (
  id uuid primary key default gen_random_uuid(),
  application_step_id uuid not null references application_steps(id) on delete cascade,
  sla_days int not null,
  due_at timestamptz not null,
  status sla_status not null default 'on_track',
  last_checked_at timestamptz not null default now()
);

create table notifications (
  id uuid primary key default gen_random_uuid(),
  citizen_id uuid not null references citizens(id) on delete cascade,
  title text not null,
  body text not null,
  notification_type text not null default 'info',
  read_at timestamptz,
  created_at timestamptz not null default now()
);

create table audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid,
  actor_role text not null default 'citizen',
  action text not null,
  resource_type text not null,
  resource_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table district_analytics (
  id uuid primary key default gen_random_uuid(),
  district text not null,
  metric_date date not null,
  applications_count int not null default 0,
  breached_count int not null default 0,
  avg_turnaround_hours numeric,
  unique (district, metric_date)
);

-- ---------------------------------------------------------------------
-- Officials (staff accessing the admin dashboard)
-- ---------------------------------------------------------------------

create table officials (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null,
  role official_role not null default 'department_officer',
  department text,
  district text,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------

alter table citizens enable row level security;
alter table profiles enable row level security;
alter table documents enable row level security;
alter table document_verifications enable row level security;
alter table applications enable row level security;
alter table application_steps enable row level security;
alter table consents enable row level security;
alter table connector_requests enable row level security;
alter table connector_events enable row level security;
alter table sla_records enable row level security;
alter table notifications enable row level security;
alter table audit_logs enable row level security;

-- helper: is the current user an official, and with which scope
create or replace function is_official()
returns boolean
language sql
stable
as $$
  select exists (select 1 from officials where id = auth.uid());
$$;

create or replace function official_district()
returns text
language sql
stable
as $$
  select district from officials where id = auth.uid();
$$;

-- citizens: a citizen sees only their own row; officials see rows in
-- their district (district_admin/super_admin) or all (super_admin).
create policy citizens_self_select on citizens
  for select using (
    id = auth.uid()
    or (is_official() and (district = official_district() or
        exists (select 1 from officials o where o.id = auth.uid() and o.role = 'super_admin')))
  );

create policy citizens_self_update on citizens
  for update using (id = auth.uid());

create policy citizens_self_insert on citizens
  for insert with check (id = auth.uid());

create policy profiles_owner on profiles
  for all using (citizen_id = auth.uid()) with check (citizen_id = auth.uid());

create policy documents_owner on documents
  for all using (citizen_id = auth.uid()) with check (citizen_id = auth.uid());

create policy document_verifications_owner on document_verifications
  for select using (
    exists (select 1 from documents d where d.id = document_id and d.citizen_id = auth.uid())
    or is_official()
  );

create policy applications_owner on applications
  for all using (citizen_id = auth.uid() or is_official())
  with check (citizen_id = auth.uid());

create policy application_steps_owner on application_steps
  for select using (
    exists (select 1 from applications a where a.id = application_id and a.citizen_id = auth.uid())
    or is_official()
  );

create policy consents_owner on consents
  for all using (citizen_id = auth.uid()) with check (citizen_id = auth.uid());

create policy connector_requests_visibility on connector_requests
  for select using (
    exists (
      select 1 from application_steps s
      join applications a on a.id = s.application_id
      where s.id = application_step_id and a.citizen_id = auth.uid()
    )
    or is_official()
  );

create policy connector_events_visibility on connector_events
  for select using (
    exists (
      select 1 from connector_requests cr
      join application_steps s on s.id = cr.application_step_id
      join applications a on a.id = s.application_id
      where cr.id = connector_request_id and a.citizen_id = auth.uid()
    )
    or is_official()
  );

create policy sla_records_visibility on sla_records
  for select using (is_official() or
    exists (
      select 1 from application_steps s
      join applications a on a.id = s.application_id
      where s.id = application_step_id and a.citizen_id = auth.uid()
    )
  );

create policy notifications_owner on notifications
  for all using (citizen_id = auth.uid()) with check (citizen_id = auth.uid());

create policy audit_logs_official_read on audit_logs
  for select using (is_official());

-- service catalog + district_analytics are public read (no PII), writes
-- restricted to service_role (backend) only — no policy needed beyond RLS
-- default-deny for anon/authenticated writes.
alter table services enable row level security;
alter table life_events enable row level security;
alter table service_dependencies enable row level security;
alter table district_analytics enable row level security;

create policy services_public_read on services for select using (true);
create policy life_events_public_read on life_events for select using (true);
create policy service_dependencies_public_read on service_dependencies for select using (true);
create policy district_analytics_official_read on district_analytics for select using (is_official());
