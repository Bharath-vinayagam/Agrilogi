"""
OTP Service for secure phone verification.
Implements rate limiting, expiration, attempt limits, and resend cooldown.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from twilio.rest import Client
from database.db import supabase_client
from settings import settings


class OTPService:
    """Secure OTP generation, sending, and verification service."""
    
    # Configuration
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 3
    RESEND_COOLDOWN_SECONDS = 60
    MAX_DAILY_SENDS = 10
    
    def __init__(self):
        """Initialize Twilio client if credentials are available."""
        self.twilio_client = None
        
        if settings.twilio_account_sid and settings.twilio_auth_token:
            try:
                self.twilio_client = Client(
                    settings.twilio_account_sid,
                    settings.twilio_auth_token
                )
            except Exception as e:
                print(f"⚠️  Twilio initialization failed: {e}")
    
    def _generate_otp(self) -> str:
        """Generate a secure 6-digit OTP."""
        return ''.join([str(secrets.randbelow(10)) for _ in range(self.OTP_LENGTH)])
    
    def _hash_otp(self, otp: str) -> str:
        """Hash OTP for secure storage (never store plaintext OTP)."""
        return hashlib.sha256(otp.encode()).hexdigest()
    
    def _verify_otp_hash(self, otp: str, hashed_otp: str) -> bool:
        """Verify OTP against stored hash."""
        return self._hash_otp(otp) == hashed_otp
    
    def _send_sms(self, phone: str, otp: str) -> bool:
        """Send OTP via Twilio SMS."""
        if not self.twilio_client or not settings.twilio_phone_number:
            print(f"⚠️  Twilio not configured. OTP for {phone}: {otp}")
            return False
        
        try:
            message = self.twilio_client.messages.create(
                body=f"Your Agrilogi verification code is: {otp}. Valid for {self.OTP_EXPIRY_MINUTES} minutes. Do not share this code.",
                from_=settings.twilio_phone_number,
                to=phone
            )
            
            print(f"✅ OTP sent to {phone}: {message.sid}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send OTP to {phone}: {e}")
            return False
    
    def _check_rate_limit(self, user_id: str, phone: str) -> Tuple[bool, Optional[str]]:
        """Check if user has exceeded rate limits."""
        if not supabase_client:
            return True, None
        
        try:
            # Get user's OTP sending history
            response = supabase_client.table("users").select(
                "otp_last_sent_at, phone"
            ).eq("id", user_id).single().execute()
            
            if not response.data:
                return True, None
            
            last_sent = response.data.get("otp_last_sent_at")
            
            # Check resend cooldown
            if last_sent:
                last_sent_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                cooldown_remaining = self.RESEND_COOLDOWN_SECONDS - (datetime.now(last_sent_dt.tzinfo) - last_sent_dt).total_seconds()
                
                if cooldown_remaining > 0:
                    return False, f"Please wait {int(cooldown_remaining)} seconds before requesting another OTP."
            
            # Check daily limit
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            logs_response = supabase_client.table("verification_logs").select(
                "id"
            ).eq("user_id", user_id).eq("verification_type", "phone_otp").gte(
                "created_at", today_start.isoformat()
            ).execute()
            
            if len(logs_response.data) >= self.MAX_DAILY_SENDS:
                return False, f"Daily OTP limit ({self.MAX_DAILY_SENDS}) reached. Please try tomorrow."
            
            return True, None
            
        except Exception as e:
            print(f"❌ Rate limit check failed: {e}")
            return True, None  # Allow on error (fail open for user experience)
    
    def send_otp(
        self,
        user_id: str,
        phone: str,
        name: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Generate and send OTP to user's phone.
        
        Returns:
            dict with 'success', 'message', and optionally 'otp' (dev mode only)
        """
        if not supabase_client:
            return {"success": False, "message": "Database not available"}
        
        # Check rate limits
        allowed, error_msg = self._check_rate_limit(user_id, phone)
        if not allowed:
            return {"success": False, "message": error_msg}
        
        # Generate OTP
        otp = self._generate_otp()
        hashed_otp = self._hash_otp(otp)
        expires_at = datetime.now() + timedelta(minutes=self.OTP_EXPIRY_MINUTES)
        
        try:
            # Store hashed OTP in database
            update_response = supabase_client.table("users").update({
                "otp_code": hashed_otp,
                "otp_expires_at": expires_at.isoformat(),
                "otp_attempts": 0,  # Reset attempts on new OTP
                "otp_last_sent_at": datetime.now().isoformat()
            }).eq("id", user_id).execute()
            
            if not update_response.data:
                return {"success": False, "message": "Failed to store OTP"}
            
            # Send OTP via SMS
            sms_sent = self._send_sms(phone, otp)
            
            # Log verification attempt
            supabase_client.table("verification_logs").insert({
                "user_id": user_id,
                "verification_type": "phone_otp",
                "status": "initiated" if sms_sent else "failed",
                "details": {
                    "phone": phone,
                    "sms_sent": sms_sent,
                    "expires_at": expires_at.isoformat()
                }
            }).execute()
            
            result = {
                "success": True,
                "message": f"OTP sent to {phone}. Valid for {self.OTP_EXPIRY_MINUTES} minutes.",
                "expires_at": expires_at.isoformat()
            }
            
            # In development, include OTP in response for testing
            if settings.app_env == "development" and not sms_sent:
                result["otp"] = otp  # ONLY for dev/testing
                result["message"] += f" [DEV MODE: OTP is {otp}]"
            
            return result
            
        except Exception as e:
            print(f"❌ Send OTP failed: {e}")
            return {"success": False, "message": "Failed to send OTP. Please try again."}
    
    def verify_otp(
        self,
        user_id: str,
        otp: str,
        phone: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Verify OTP provided by user.
        
        Returns:
            dict with 'success', 'message', and 'verified' status
        """
        if not supabase_client:
            return {"success": False, "message": "Database not available"}
        
        if not otp or len(otp) != self.OTP_LENGTH:
            return {"success": False, "message": "Invalid OTP format"}
        
        try:
            # Get user's stored OTP data
            response = supabase_client.table("users").select(
                "id, phone, otp_code, otp_expires_at, otp_attempts, phone_verified"
            ).eq("id", user_id).single().execute()
            
            if not response.data:
                return {"success": False, "message": "User not found"}
            
            user_data = response.data
            
            # Check if phone is already verified
            if user_data.get("phone_verified"):
                return {
                    "success": True,
                    "message": "Phone already verified",
                    "verified": True
                }
            
            # Check if OTP exists
            if not user_data.get("otp_code"):
                return {"success": False, "message": "No OTP found. Please request a new one."}
            
            # Check expiration
            expires_at = datetime.fromisoformat(user_data["otp_expires_at"].replace('Z', '+00:00'))
            if datetime.now(expires_at.tzinfo) > expires_at:
                # Clear expired OTP
                supabase_client.table("users").update({
                    "otp_code": None,
                    "otp_expires_at": None
                }).eq("id", user_id).execute()
                
                return {"success": False, "message": "OTP expired. Please request a new one."}
            
            # Check attempts limit
            attempts = user_data.get("otp_attempts", 0)
            if attempts >= self.MAX_ATTEMPTS:
                # Lock out user
                supabase_client.table("users").update({
                    "otp_code": None,
                    "otp_expires_at": None
                }).eq("id", user_id).execute()
                
                return {"success": False, "message": f"Too many failed attempts. Please request a new OTP."}
            
            # Verify OTP
            if self._verify_otp_hash(otp, user_data["otp_code"]):
                # OTP is correct - mark phone as verified
                supabase_client.table("users").update({
                    "phone_verified": True,
                    "phone_verified_at": datetime.now().isoformat(),
                    "otp_code": None,  # Clear OTP
                    "otp_expires_at": None,
                    "otp_attempts": 0
                }).eq("id", user_id).execute()
                
                # Log success
                supabase_client.table("verification_logs").insert({
                    "user_id": user_id,
                    "verification_type": "phone_otp",
                    "status": "success",
                    "details": {"phone": user_data["phone"]}
                }).execute()
                
                return {
                    "success": True,
                    "message": "Phone verified successfully!",
                    "verified": True
                }
            else:
                # Incorrect OTP - increment attempts
                new_attempts = attempts + 1
                supabase_client.table("users").update({
                    "otp_attempts": new_attempts
                }).eq("id", user_id).execute()
                
                remaining = self.MAX_ATTEMPTS - new_attempts
                
                # Log failure
                supabase_client.table("verification_logs").insert({
                    "user_id": user_id,
                    "verification_type": "phone_otp",
                    "status": "failed",
                    "details": {
                        "phone": user_data["phone"],
                        "attempts": new_attempts
                    }
                }).execute()
                
                if remaining > 0:
                    return {
                        "success": False,
                        "message": f"Incorrect OTP. {remaining} attempt(s) remaining."
                    }
                else:
                    # Clear OTP after max attempts
                    supabase_client.table("users").update({
                        "otp_code": None,
                        "otp_expires_at": None
                    }).eq("id", user_id).execute()
                    
                    return {
                        "success": False,
                        "message": "Too many failed attempts. Please request a new OTP."
                    }
                    
        except Exception as e:
            print(f"❌ Verify OTP failed: {e}")
            return {"success": False, "message": "Verification failed. Please try again."}
    
    def check_verification_status(self, user_id: str) -> Dict[str, any]:
        """Check if user's phone is verified."""
        if not supabase_client:
            return {"verified": False}
        
        try:
            response = supabase_client.table("users").select(
                "phone_verified, phone_verified_at"
            ).eq("id", user_id).single().execute()
            
            if response.data:
                return {
                    "verified": response.data.get("phone_verified", False),
                    "verified_at": response.data.get("phone_verified_at")
                }
            
            return {"verified": False}
            
        except Exception as e:
            print(f"❌ Check verification status failed: {e}")
            return {"verified": False}


# Singleton instance
otp_service = OTPService()
