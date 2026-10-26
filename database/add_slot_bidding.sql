-- Extend bids table to support slot-level bidding
-- This allows drivers to bid on specific time slots (date + slot) in addition to bundles

ALTER TABLE bids
ADD COLUMN IF NOT EXISTS pickup_date DATE,
ADD COLUMN IF NOT EXISTS pickup_slot VARCHAR(20),
ADD COLUMN IF NOT EXISTS bid_type VARCHAR(20) DEFAULT 'bundle';

-- Create index for efficient querying by date and slot
CREATE INDEX IF NOT EXISTS idx_bids_pickup_date_slot ON bids(pickup_date, pickup_slot);
CREATE INDEX IF NOT EXISTS idx_bids_type ON bids(bid_type);

-- Add composite index for slot bid queries
CREATE INDEX IF NOT EXISTS idx_bids_slot_composite ON bids(pickup_date, pickup_slot, bid_type) WHERE bid_type = 'slot';

COMMENT ON COLUMN bids.bid_type IS 'Values: bundle, slot - determines if bid is for a bundle or time slot';
COMMENT ON COLUMN bids.pickup_date IS 'For slot bids: the date of the time slot being bid on';
COMMENT ON COLUMN bids.pickup_slot IS 'For slot bids: the time slot (morning, afternoon, evening)';
