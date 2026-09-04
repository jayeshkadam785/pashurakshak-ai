-- PashuRakshak — Supabase schema
-- Run this in the Supabase SQL editor for your project.

create table if not exists reports (
  id uuid primary key default gen_random_uuid(),
  village text not null,
  block text,
  lat double precision,
  lng double precision,
  animal_type text,
  symptoms text[] default '{}',
  affected_count integer default 1,
  days_since_onset integer default 0,
  notes text,
  risk_level text,          -- 'low' | 'moderate' | 'high'
  risk_score integer,
  reported_by uuid,         -- optional: references auth.users
  date date default current_date,
  created_at timestamptz default now()
);

create table if not exists animals (
  id uuid primary key default gen_random_uuid(),
  tag_id text unique not null,
  species text,
  owner_id uuid,            -- optional: references auth.users
  village text,
  last_vaccination date,
  next_due date,
  recent_treatment text,
  status text default 'healthy'   -- 'healthy' | 'under_care' | 'vaccination_overdue'
);

create table if not exists advisories (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  body text not null,
  severity text not null,   -- 'low' | 'moderate' | 'high'
  issued_by text,
  block text,
  created_at timestamptz default now()
);

-- Helpful indexes for the dashboard queries
create index if not exists reports_date_idx on reports (date desc);
create index if not exists reports_village_idx on reports (village);
