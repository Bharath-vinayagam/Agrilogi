-- Create bid_history table to track all bidding activity
-- This provides complete audit trail of driver bidding behavior

CREATE TABLE IF NOT EXISTS bid_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  bid_id TEXT NOT NULL REFERENCES bids(id) ON DELETE CASCADE,
  driver_id UUID REFERENCES drivers(id) ON DELETE SET NULL,
  driver_name TEXT NOT NULL,
  cluster_id TEXT,
  order_id TEXT,
  pickup_date DATE,
  pickup_slot VARCHAR(20),
  bid_amount INTEGER NOT NULL,
  vehicle TEXT NOT NULL,
  reliability_score INTEGER DEFAULT 94,
  bid_type VARCHAR(20) NOT NULL CHECK (bid_type IN ('bundle', 'slot', 'order', 'cluster')),
  bid_status VARCHAR(20) NOT NULL CHECK (bid_status IN ('Open', 'Accepted', 'Closed', 'Rejected', 'Withdrawn')),
  status_changed_at TIMESTAMPTZ DEFAULT NOW(),
  won BOOLEAN DEFAULT FALSE,
  rejection_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_bid_history_driver_name ON bid_history(driver_name);
CREATE INDEX IF NOT EXISTS idx_bid_history_bid_id ON bid_history(bid_id);
CREATE INDEX IF NOT EXISTS idx_bid_history_cluster_id ON bid_history(cluster_id);
CREATE INDEX IF NOT EXISTS idx_bid_history_created_at ON bid_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bid_history_driver_status ON bid_history(driver_name, bid_status);
CREATE INDEX IF NOT EXISTS idx_bid_history_won ON bid_history(driver_name, won) WHERE won = TRUE;

-- Composite index for driver bidding activity queries
CREATE INDEX IF NOT EXISTS idx_bid_history_driver_activity ON bid_history(driver_name, created_at DESC, bid_status);

COMMENT ON TABLE bid_history IS 'Audit trail of all bidding activity - tracks wins, losses, withdrawals';
COMMENT ON COLUMN bid_history.bid_id IS 'Reference to the original bid in bids table';
COMMENT ON COLUMN bid_history.won IS 'True if bid was accepted (driver won the cluster)';
COMMENT ON COLUMN bid_history.rejection_reason IS 'Why bid was rejected (capacity, timing conflict, etc.)';
COMMENT ON COLUMN bid_history.status_changed_at IS 'When the bid status last changed';

-- Function to automatically log bid status changes
CREATE OR REPLACE FUNCTION log_bid_status_change()
RETURNS TRIGGER AS $$
BEGIN
  -- Only log if status changed
  IF (TG_OP = 'UPDATE' AND OLD.status != NEW.status) OR TG_OP = 'INSERT' THEN
    INSERT INTO bid_history (
      bid_id,
      driver_id,
      driver_name,
      cluster_id,
      order_id,
      pickup_date,
      pickup_slot,
      bid_amount,
      vehicle,
      reliability_score,
      bid_type,
      bid_status,
      status_changed_at,
      won
    ) VALUES (
      NEW.id,
      NEW.driver_id,
      NEW.driver_name,
      NEW.bundle_id,
      NEW.order_id,
      NEW.pickup_date,
      NEW.pickup_slot,
      NEW.amount,
      NEW.vehicle,
      NEW.reliability_score,
      NEW.bid_type,
      NEW.status,
      NOW(),
      (NEW.status = 'Accepted')
    );
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-log bid changes
DROP TRIGGER IF EXISTS trigger_log_bid_changes ON bids;
CREATE TRIGGER trigger_log_bid_changes
AFTER INSERT OR UPDATE ON bids
FOR EACH ROW
EXECUTE FUNCTION log_bid_status_change();

COMMENT ON FUNCTION log_bid_status_change IS 'Automatically logs bid status changes to bid_history table';
COMMENT ON TRIGGER trigger_log_bid_changes ON bids IS 'Captures all bid status changes for audit trail';
