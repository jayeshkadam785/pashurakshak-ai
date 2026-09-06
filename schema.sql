-- =========================================================
-- PASHURAKSHAK AI
-- LIVESTOCK HEALTH DATABASE
-- Supabase PostgreSQL + PostGIS
-- =========================================================

create extension if not exists postgis;
create extension if not exists pgcrypto;

-- =========================================================
-- 1. REPORTS
-- =========================================================

create table if not exists reports (
    id uuid primary key default gen_random_uuid(),

    village text,
    block text,

    latitude double precision,
    longitude double precision,

    animal_type text not null default 'cattle',

    symptoms jsonb not null default '[]'::jsonb,

    affected_count integer not null default 1
        check (affected_count >= 1),

    days_since_onset integer default 1
        check (days_since_onset >= 0),

    vaccination_status text default 'unknown',

    notes text,

    -- AI prediction
    risk_level text default 'LOW'
        check (risk_level in ('LOW', 'MODERATE', 'HIGH', 'CLUSTER')),

    risk_score integer default 0
        check (risk_score >= 0 and risk_score <= 100),

    confidence integer default 0
        check (confidence >= 0 and confidence <= 100),

    risk_factors jsonb default '[]'::jsonb,

    recommendation text,

    screening_type text default 'AI-assisted decision support',

    -- Reporter
    reported_by text,

    -- Status
    case_status text default 'OPEN'
        check (
            case_status in (
                'OPEN',
                'UNDER_REVIEW',
                'VERIFIED',
                'TREATMENT',
                'ISOLATED',
                'CLOSED'
            )
        ),

    vet_verified boolean default false,

    -- Dates
    date date default current_date,

    created_at timestamptz default now(),

    updated_at timestamptz default now()
);

-- =========================================================
-- 2. IMAGE SCREENINGS
-- =========================================================

create table if not exists image_screenings (
    id uuid primary key default gen_random_uuid(),

    report_id uuid references reports(id)
        on delete set null,

    image_url text,

    image_name text,

    visible_signs jsonb default '[]'::jsonb,

    possible_categories jsonb default '[]'::jsonb,

    risk_level text default 'LOW'
        check (risk_level in ('LOW', 'MODERATE', 'HIGH', 'CLUSTER')),

    confidence integer default 0
        check (confidence >= 0 and confidence <= 100),

    recommendation text,

    model_name text default 'AI Image Screening',

    created_at timestamptz default now()
);

-- =========================================================
-- 3. ANIMALS
-- =========================================================

create table if not exists animals (
    id uuid primary key default gen_random_uuid(),

    tag_id text unique,

    species text not null,

    owner_id text,

    village text,

    age_years numeric,

    gender text,

    last_vaccination date,

    next_due date,

    recent_treatment text,

    status text default 'HEALTHY'
        check (
            status in (
                'HEALTHY',
                'WATCH',
                'SICK',
                'ISOLATED',
                'RECOVERED'
            )
        ),

    created_at timestamptz default now(),

    updated_at timestamptz default now()
);

-- =========================================================
-- 4. ADVISORIES
-- =========================================================

create table if not exists advisories (
    id uuid primary key default gen_random_uuid(),

    title text not null,

    message text not null,

    language text default 'en',

    target_role text default 'all',

    severity text default 'INFO'
        check (
            severity in (
                'INFO',
                'WARNING',
                'URGENT',
                'CRITICAL'
            )
        ),

    active boolean default true,

    created_at timestamptz default now()
);

-- =========================================================
-- 5. OUTBREAK / HOTSPOT CLUSTERS
-- =========================================================

create table if not exists outbreak_clusters (
    id uuid primary key default gen_random_uuid(),

    cluster_name text,

    village text,

    block text,

    center_latitude double precision,

    center_longitude double precision,

    radius_km numeric default 1,

    case_count integer default 0,

    affected_animals integer default 0,

    risk_score integer default 0
        check (risk_score >= 0 and risk_score <= 100),

    risk_level text default 'MODERATE'
        check (
            risk_level in (
                'LOW',
                'MODERATE',
                'HIGH',
                'CLUSTER'
            )
        ),

    suspected_disease text,

    detected_at timestamptz default now(),

    status text default 'ACTIVE'
        check (
            status in (
                'ACTIVE',
                'MONITORING',
                'RESOLVED'
            )
        ),

    created_at timestamptz default now(),

    updated_at timestamptz default now()
);

-- =========================================================
-- 6. ALERTS
-- =========================================================

create table if not exists alerts (
    id uuid primary key default gen_random_uuid(),

    report_id uuid references reports(id)
        on delete cascade,

    cluster_id uuid references outbreak_clusters(id)
        on delete set null,

    alert_type text not null,

    title text not null,

    message text not null,

    severity text default 'WARNING'
        check (
            severity in (
                'INFO',
                'WARNING',
                'URGENT',
                'CRITICAL'
            )
        ),

    target_role text default 'vet',

    village text,

    acknowledged boolean default false,

    acknowledged_by text,

    acknowledged_at timestamptz,

    created_at timestamptz default now()
);

-- =========================================================
-- 7. VACCINATION RECORDS
-- =========================================================

create table if not exists vaccination_records (
    id uuid primary key default gen_random_uuid(),

    animal_id uuid references animals(id)
        on delete cascade,

    vaccine_name text not null,

    vaccination_date date,

    next_due_date date,

    administered_by text,

    notes text,

    created_at timestamptz default now()
);

-- =========================================================
-- 8. TREATMENT RECORDS
-- =========================================================

create table if not exists treatment_records (
    id uuid primary key default gen_random_uuid(),

    animal_id uuid references animals(id)
        on delete cascade,

    report_id uuid references reports(id)
        on delete set null,

    treatment_name text,

    diagnosis text,

    veterinarian text,

    treatment_date date default current_date,

    follow_up_date date,

    outcome text,

    notes text,

    created_at timestamptz default now()
);

-- =========================================================
-- 9. AUDIT LOG
-- =========================================================

create table if not exists audit_logs (
    id uuid primary key default gen_random_uuid(),

    user_id text,

    user_role text,

    action text not null,

    resource_type text,

    resource_id text,

    ip_address text,

    user_agent text,

    metadata jsonb default '{}'::jsonb,

    created_at timestamptz default now()
);

-- =========================================================
-- 10. INDEXES
-- =========================================================

create index if not exists idx_reports_date
on reports(date);

create index if not exists idx_reports_village
on reports(village);

create index if not exists idx_reports_block
on reports(block);

create index if not exists idx_reports_risk
on reports(risk_level);

create index if not exists idx_reports_score
on reports(risk_score);

create index if not exists idx_reports_created
on reports(created_at);

create index if not exists idx_image_report
on image_screenings(report_id);

create index if not exists idx_clusters_risk
on outbreak_clusters(risk_level);

create index if not exists idx_clusters_village
on outbreak_clusters(village);

create index if not exists idx_alerts_status
on alerts(acknowledged);

create index if not exists idx_vaccination_animal
on vaccination_records(animal_id);

create index if not exists idx_treatment_animal
on treatment_records(animal_id);

-- =========================================================
-- 11. GEO INDEX
-- =========================================================

create index if not exists idx_reports_geo
on reports
using gist (
    ST_SetSRID(
        ST_MakePoint(longitude, latitude),
        4326
    )
);

-- =========================================================
-- 12. UPDATED_AT TRIGGER
-- =========================================================

create or replace function update_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists reports_updated_at
on reports;

create trigger reports_updated_at
before update on reports
for each row
execute function update_updated_at();


drop trigger if exists animals_updated_at
on animals;

create trigger animals_updated_at
before update on animals
for each row
execute function update_updated_at();


drop trigger if exists clusters_updated_at
on outbreak_clusters;

create trigger clusters_updated_at
before update on outbreak_clusters
for each row
execute function update_updated_at();

-- =========================================================
-- 13. SUPABASE ROW LEVEL SECURITY
-- =========================================================

alter table reports enable row level security;
alter table animals enable row level security;
alter table advisories enable row level security;
alter table image_screenings enable row level security;
alter table outbreak_clusters enable row level security;
alter table alerts enable row level security;
alter table vaccination_records enable row level security;
alter table treatment_records enable row level security;
alter table audit_logs enable row level security;

-- =========================================================
-- 14. DEMO POLICIES
-- =========================================================
-- For the prototype/demo.
-- Production deployment should use Supabase Auth
-- and role-based policies.

drop policy if exists "reports_public_read" on reports;

create policy "reports_public_read"
on reports
for select
using (true);


drop policy if exists "reports_public_insert" on reports;

create policy "reports_public_insert"
on reports
for insert
with check (true);


drop policy if exists "image_screenings_read" on image_screenings;

create policy "image_screenings_read"
on image_screenings
for select
using (true);


drop policy if exists "image_screenings_insert" on image_screenings;

create policy "image_screenings_insert"
on image_screenings
for insert
with check (true);


drop policy if exists "animals_read" on animals;

create policy "animals_read"
on animals
for select
using (true);


drop policy if exists "advisories_read" on advisories;

create policy "advisories_read"
on advisories
for select
using (active = true);


drop policy if exists "clusters_read" on outbreak_clusters;

create policy "clusters_read"
on outbreak_clusters
for select
using (true);


drop policy if exists "alerts_read" on alerts;

create policy "alerts_read"
on alerts
for select
using (true);

-- =========================================================
-- END PASHURAKSHAK AI DATABASE
-- =========================================================
