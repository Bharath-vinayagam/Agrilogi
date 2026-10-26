-- Add missing columns to trip_assignments table
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS driver_name text;
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS cluster_id text;
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS bid_id text;
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS contract_value integer;
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS status text DEFAULT 'Assigned';
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS assigned_at timestamptz DEFAULT now();

-- Update driver_name for existing records where it's null
UPDATE trip_assignments 
SET driver_name = users.name 
FROM users 
WHERE trip_assignments.driver_id = users.id 
  AND trip_assignments.driver_name IS NULL;

-- Update cluster_id from bundle_id if exists
UPDATE trip_assignments 
SET cluster_id = bundle_id 
WHERE cluster_id IS NULL AND bundle_id IS NOT NULL;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_trip_assignments_driver_name ON trip_assignments(driver_name);
CREATE INDEX IF NOT EXISTS idx_trip_assignments_cluster ON trip_assignments(cluster_id);
CREATE INDEX IF NOT EXISTS idx_trip_assignments_status ON trip_assignments(status);

-- Make driver_name and cluster_id NOT NULL after data migration
ALTER TABLE trip_assignments ALTER COLUMN driver_name SET NOT NULL;
ALTER TABLE trip_assignments ALTER COLUMN cluster_id SET NOT NULL;
