-- Migration: Add verification fields for secure authentication
-- Date: 2026-10-15
-- Purpose: Add OTP verification, vehicle verification, license verification, and enhanced location support

-- Add verification fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS phone_verified_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS otp_code TEXT,
ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS otp_attempts INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS otp_last_sent_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS city TEXT,
ADD COLUMN IF NOT EXISTS district TEXT,
ADD COLUMN IF NOT EXISTS state TEXT,
ADD COLUMN IF NOT EXISTS pin_code TEXT;

-- Add verification fields to drivers table
ALTER TABLE drivers
ADD COLUMN IF NOT EXISTS vehicle_verification_status TEXT DEFAULT 'pending' CHECK (vehicle_verification_status IN ('pending', 'verified', 'failed', 'manual_review')),
ADD COLUMN IF NOT EXISTS vehicle_verified_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS vehicle_verification_details JSONB,
ADD COLUMN IF NOT EXISTS license_verification_status TEXT DEFAULT 'pending' CHECK (license_verification_status IN ('pending', 'verified', 'failed', 'manual_review')),
ADD COLUMN IF NOT EXISTS license_verified_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS license_verification_details JSONB,
ADD COLUMN IF NOT EXISTS account_status TEXT DEFAULT 'pending_verification' CHECK (account_status IN ('pending_verification', 'active', 'suspended', 'deactivated')),
ADD COLUMN IF NOT EXISTS city TEXT,
ADD COLUMN IF NOT EXISTS district TEXT,
ADD COLUMN IF NOT EXISTS state TEXT,
ADD COLUMN IF NOT EXISTS pin_code TEXT;

-- Create verification_logs table for audit trail
CREATE TABLE IF NOT EXISTS verification_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  verification_type TEXT NOT NULL CHECK (verification_type IN ('phone_otp', 'vehicle', 'license')),
  status TEXT NOT NULL CHECK (status IN ('initiated', 'success', 'failed', 'expired')),
  details JSONB,
  ip_address TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster OTP lookups
CREATE INDEX IF NOT EXISTS idx_users_phone_otp ON users(phone, otp_code) WHERE otp_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_phone_verified ON users(phone_verified);
CREATE INDEX IF NOT EXISTS idx_drivers_verification_status ON drivers(vehicle_verification_status, license_verification_status);
CREATE INDEX IF NOT EXISTS idx_verification_logs_user_type ON verification_logs(user_id, verification_type, created_at DESC);

-- Add comments for documentation
COMMENT ON COLUMN users.phone_verified IS 'Whether phone number has been verified via OTP';
COMMENT ON COLUMN users.otp_code IS 'Current OTP code (hashed), expires after otp_expires_at';
COMMENT ON COLUMN users.otp_expires_at IS 'Expiration timestamp for current OTP (typically 5 minutes)';
COMMENT ON COLUMN users.otp_attempts IS 'Number of failed OTP verification attempts (reset on success)';
COMMENT ON COLUMN users.otp_last_sent_at IS 'Last time OTP was sent (for rate limiting)';

COMMENT ON COLUMN drivers.vehicle_verification_status IS 'Vehicle registration verification status';
COMMENT ON COLUMN drivers.license_verification_status IS 'Driving license verification status';
COMMENT ON COLUMN drivers.account_status IS 'Overall driver account status based on verifications';

COMMENT ON TABLE verification_logs IS 'Audit log for all verification attempts (OTP, vehicle, license)';
