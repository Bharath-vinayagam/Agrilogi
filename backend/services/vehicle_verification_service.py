"""
Vehicle Verification Service.
Validates Indian vehicle registration numbers and integrates with verification APIs.
"""

import re
from datetime import datetime
from typing import Dict, Optional
from database.db import supabase_client


class VehicleVerificationService:
    """Service for vehicle registration verification."""
    
    # Indian vehicle registration number patterns
    # Format: XX YY ZZ #### or XX-YY-ZZ-#### or XXYYZZ####
    # XX = State code (2 letters)
    # YY = District code (2 digits)
    # ZZ = Series (1-2 letters)
    # #### = Number (1-4 digits)
    
    PATTERNS = [
        # Standard format: TN 11 AB 4472
        re.compile(r'^([A-Z]{2})\s*(\d{1,2})\s*([A-Z]{1,2})\s*(\d{1,4})$', re.IGNORECASE),
        # With hyphens: TN-11-AB-4472
        re.compile(r'^([A-Z]{2})-(\d{1,2})-([A-Z]{1,2})-(\d{1,4})$', re.IGNORECASE),
        # No separators: TN11AB4472
        re.compile(r'^([A-Z]{2})(\d{1,2})([A-Z]{1,2})(\d{1,4})$', re.IGNORECASE),
    ]
    
    # Valid Indian state codes
    STATE_CODES = {
        'AP', 'AR', 'AS', 'BR', 'CG', 'CH', 'DD', 'DL', 'GA', 'GJ',
        'HP', 'HR', 'JH', 'JK', 'KA', 'KL', 'LA', 'LD', 'MH', 'ML',
        'MN', 'MP', 'MZ', 'NL', 'OD', 'OR', 'PB', 'PY', 'RJ', 'SK',
        'TN', 'TR', 'TS', 'UK', 'UP', 'WB', 'AN', 'DN', 'HP'
    }
    
    def __init__(self):
        """Initialize vehicle verification service."""
        # In production, initialize with vehicle verification API credentials
        # Examples: Parivahan API, third-party vehicle data providers
        self.api_available = False  # Set to True when API is configured
    
    def validate_format(self, vehicle_number: str) -> Dict[str, any]:
        """
        Validate vehicle registration number format.
        
        Returns:
            dict with 'valid', 'normalized', 'components', and 'message'
        """
        if not vehicle_number:
            return {
                "valid": False,
                "message": "Vehicle number is required"
            }
        
        # Remove extra whitespace
        vehicle_number = vehicle_number.strip()
        
        # Try each pattern
        for pattern in self.PATTERNS:
            match = pattern.match(vehicle_number)
            if match:
                state, district, series, number = match.groups()
                state = state.upper()
                series = series.upper()
                
                # Validate state code
                if state not in self.STATE_CODES:
                    return {
                        "valid": False,
                        "message": f"Invalid state code: {state}"
                    }
                
                # Normalize format: XX YY ZZ ####
                normalized = f"{state} {district.zfill(2)} {series} {number.zfill(4)}"
                
                return {
                    "valid": True,
                    "normalized": normalized,
                    "components": {
                        "state": state,
                        "district": district.zfill(2),
                        "series": series,
                        "number": number.zfill(4)
                    },
                    "message": "Format valid"
                }
        
        return {
            "valid": False,
            "message": "Invalid vehicle registration format. Expected format: TN 11 AB 4472"
        }
    
    def verify_vehicle(
        self,
        driver_id: str,
        vehicle_number: str,
        owner_name: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Verify vehicle registration against external API or mark for manual review.
        
        Returns:
            dict with 'status', 'verified', 'details', and 'message'
        """
        if not supabase_client:
            return {
                "status": "failed",
                "verified": False,
                "message": "Database not available"
            }
        
        # Step 1: Validate format
        format_result = self.validate_format(vehicle_number)
        if not format_result["valid"]:
            return {
                "status": "failed",
                "verified": False,
                "message": format_result["message"]
            }
        
        normalized = format_result["normalized"]
        
        try:
            # Step 2: Check if API is available for automatic verification
            if self.api_available:
                # TODO: Integrate with vehicle verification API
                # Example: Parivahan RTO API, third-party services
                
                # api_result = self._call_verification_api(normalized, owner_name)
                # if api_result["verified"]:
                #     status = "verified"
                #     details = api_result["details"]
                # else:
                #     status = "failed"
                #     details = api_result
                
                pass
            
            # Step 3: If no API, mark for manual review
            status = "manual_review"
            details = {
                "vehicle_number": normalized,
                "components": format_result["components"],
                "owner_name": owner_name,
                "reason": "Automatic verification not available. Pending manual review by admin.",
                "verified_at": None
            }
            
            # Step 4: Update driver record
            update_response = supabase_client.table("drivers").update({
                "vehicle_verification_status": status,
                "vehicle_verification_details": details,
                "vehicle_verified_at": datetime.now().isoformat() if status == "verified" else None
            }).eq("id", driver_id).execute()
            
            if not update_response.data:
                return {
                    "status": "failed",
                    "verified": False,
                    "message": "Failed to update verification status"
                }
            
            # Step 5: Log verification attempt
            supabase_client.table("verification_logs").insert({
                "user_id": update_response.data[0].get("user_id"),
                "verification_type": "vehicle",
                "status": "initiated" if status == "manual_review" else status,
                "details": {
                    "driver_id": driver_id,
                    "vehicle_number": normalized,
                    "verification_method": "api" if self.api_available else "manual_review"
                }
            }).execute()
            
            # Step 6: Update account status if needed
            self._update_account_status(driver_id)
            
            message_map = {
                "verified": "Vehicle verified successfully!",
                "manual_review": "Vehicle registration submitted for manual verification. Admin will review within 24 hours.",
                "failed": "Vehicle verification failed. Please check the registration number."
            }
            
            return {
                "status": status,
                "verified": status == "verified",
                "details": details,
                "message": message_map.get(status, "Verification status updated")
            }
            
        except Exception as e:
            print(f"❌ Vehicle verification failed: {e}")
            return {
                "status": "failed",
                "verified": False,
                "message": "Verification failed. Please try again."
            }
    
    def _update_account_status(self, driver_id: str):
        """Update driver account status based on verification progress."""
        if not supabase_client:
            return
        
        try:
            # Get current verification statuses
            response = supabase_client.table("drivers").select(
                "vehicle_verification_status, license_verification_status, user_id"
            ).eq("id", driver_id).single().execute()
            
            if not response.data:
                return
            
            vehicle_status = response.data.get("vehicle_verification_status")
            license_status = response.data.get("license_verification_status")
            
            # Determine account status
            if vehicle_status == "verified" and license_status == "verified":
                account_status = "active"
            elif vehicle_status == "failed" or license_status == "failed":
                account_status = "suspended"
            else:
                account_status = "pending_verification"
            
            # Update account status
            supabase_client.table("drivers").update({
                "account_status": account_status
            }).eq("id", driver_id).execute()
            
        except Exception as e:
            print(f"❌ Failed to update account status: {e}")
    
    def get_verification_status(self, driver_id: str) -> Dict[str, any]:
        """Get vehicle verification status for a driver."""
        if not supabase_client:
            return {"status": "unknown"}
        
        try:
            response = supabase_client.table("drivers").select(
                "vehicle_verification_status, vehicle_verified_at, vehicle_verification_details"
            ).eq("id", driver_id).single().execute()
            
            if response.data:
                return {
                    "status": response.data.get("vehicle_verification_status", "pending"),
                    "verified_at": response.data.get("vehicle_verified_at"),
                    "details": response.data.get("vehicle_verification_details", {})
                }
            
            return {"status": "pending"}
            
        except Exception as e:
            print(f"❌ Failed to get verification status: {e}")
            return {"status": "unknown"}
    
    def _call_verification_api(self, vehicle_number: str, owner_name: Optional[str]) -> Dict:
        """
        Call external vehicle verification API.
        TO BE IMPLEMENTED when API credentials are available.
        """
        # Example integration with Parivahan or third-party service
        # import requests
        # 
        # response = requests.post(
        #     "https://api.example.com/vehicle/verify",
        #     json={"registration_number": vehicle_number, "owner_name": owner_name},
        #     headers={"Authorization": f"Bearer {api_key}"}
        # )
        # 
        # if response.status_code == 200:
        #     data = response.json()
        #     return {
        #         "verified": data["verified"],
        #         "details": data
        #     }
        
        return {
            "verified": False,
            "error": "API not implemented"
        }


# Singleton instance
vehicle_verification_service = VehicleVerificationService()
