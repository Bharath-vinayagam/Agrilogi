-- Trip assignments: links a driver to a bundle after winning a bid
create table if not exists trip_assignments (
  id uuid primary key default uuid_generate_v4(),
  driver_id uuid references users(id) on delete set null,
  driver_name text not null,
  cluster_id text not null,
  bid_id text,
  contract_value integer,
  status text not null default 'Assigned',
  trip_status text not null default 'Driver Assigned',
  start_time timestamptz,
  end_time timestamptz,
  assigned_at timestamptz default now(),
  created_at timestamptz default now()
);

create index if not exists idx_trip_assignments_driver on trip_assignments(driver_id);
create index if not exists idx_trip_assignments_driver_name on trip_assignments(driver_name);
create index if not exists idx_trip_assignments_cluster on trip_assignments(cluster_id);
create index if not exists idx_trip_assignments_status on trip_assignments(status);
create index if not exists idx_trip_assignments_trip_status on trip_assignments(trip_status);
