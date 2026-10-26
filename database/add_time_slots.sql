-- Add time slot fields to orders table
ALTER TABLE orders
ADD COLUMN IF NOT EXISTS pickup_date DATE,
ADD COLUMN IF NOT EXISTS pickup_slot VARCHAR(20),
ADD COLUMN IF NOT EXISTS is_time_flexible BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS estimated_delivery_time TIMESTAMP,
ADD COLUMN IF NOT EXISTS actual_pickup_time TIMESTAMP,
ADD COLUMN IF NOT EXISTS actual_delivery_time TIMESTAMP;

-- Create index for efficient querying by date and slot
CREATE INDEX IF NOT EXISTS idx_orders_pickup_date_slot ON orders(pickup_date, pickup_slot);

-- Add driver availability table (optional, for future use)
CREATE TABLE IF NOT EXISTS driver_availability (
  id SERIAL PRIMARY KEY,
  driver_id INTEGER REFERENCES users(id),
  available_date DATE NOT NULL,
  available_slot VARCHAR(20) NOT NULL,
  is_available BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(driver_id, available_date, available_slot)
);

-- Create index for driver availability
CREATE INDEX IF NOT EXISTS idx_driver_availability_date ON driver_availability(available_date, available_slot);

COMMENT ON COLUMN orders.pickup_slot IS 'Values: morning, afternoon, evening';
COMMENT ON COLUMN orders.is_time_flexible IS 'True if farmer is flexible with exact pickup time';
