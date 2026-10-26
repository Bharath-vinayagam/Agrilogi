"""
Driving License Verification Service.
Validates Indian driving license numbers and integrates with verification APIs.
"""

import re
from datetime import datetime
from typing import Dict, Optional
from database.db import supabase_client


class LicenseVerificationService:
    """Service for driving license verification."""
    
    # Indian driving license number patterns
    # Format: XX-DDDDYYYYNNNNNNN or XX DDDD YYYY NNNNNNN
    # XX = State code (2 letters)
    # DDDD = RTO code (4 digits, first 2 are district)
    # YYYY = Year of issue (4 digits)
    # NNNNNNN = Sequential number (7 digits)
    
    PATTERNS = [
        # With hyphens: DL-1420230005524
        re.compile(r'^([A-Z]{2})-?(\d{2})(\d{2})(\d{4})(\d{7})$', re.IGNORECASE),
        # With spaces: DL 14 20 2023 0005524
        re.compile(r'^([A-Z]{2})\s*(\d{2})\s*(\d{2})\s*(\d{4})\s*(\d{7})$', re.IGNORECASE),
        # No separators: DL1420230005524
        re.compile(r'^([A-Z]{2})(\d{14})$', re.IGNORECASE),
    ]
    
    # Valid state codes (same as vehicle)
    STATE_CODES = {
        'AP', 'AR', 'AS', 'BR', 'CG', 'CH', 'DD', 'DL', 'GA', 'GJ',
        'HP', 'HR', 'JH', 'JK', 'KA', 'KL', 'LA', 'LD', 'MH', 'ML',
        'MN', 'MP', 'MZ', 'NL', 'OD', 'OR', 'PB', 'PY', 'RJ', 'SK',
        'TN', 'TR', 'TS', 'UK', 'UP', 'WB', 'AN', 'DN', 'HP'
    }
    
    # Vehicle classes for commercial vehicles
    COMMERCIAL_CLASSES = {
        'LMV-TR': 'Light Motor Vehicle - Transport',
        'HMV': 'Heavy Motor Vehicle',
        'HGMV': 'Heavy Goods Motor Vehicle',
        'HPMV': 'Heavy Passenger Motor Vehicle',
        'MGV': 'Medium Goods Vehicle',
        'TRANS': 'Transport Vehicle'
    }
    
    def __init__(self):
        """Initialize license verification service."""
        # In production, initialize with license verification API credentials
        # Examples: Parivahan Sarthi API, DigiLocker integration
        self.api_available = False  # Set to True when API is configured
    
    def validate_format(self, license_number: str) -> Dict[str, any]:
        """
        Validate driving license number format.
        
        Returns:
            dict with 'valid', 'normalized', 'components', and 'message'
        """
        if not license_number:
            return {
                "valid": False,
                "message": "License number is required"
            }
        
        # Remove extra whitespace
        license_number = license_number.strip()
        
        # Try each pattern
        for idx, pattern in enumerate(self.PATTERNS):
            match = pattern.match(license_number)
            if match:
                if idx == 2:  # No separator pattern
                    state, rest = match.groups()
                    district = rest[:2]
                    rto = rest[2:4]
                    year = rest[4:8]
                    number = rest[8:]
                else:
                    state, district, rto, year, number = match.groups()
                
                state = state.upper()
                
                # Validate state code
                if state not in self.STATE_CODES:
                    return {
                        "valid": False,
                        "message": f"Invalid state code: {state}"
                    }
                
                # Validate year
                try:
                    year_int = int(year)
                    current_year = datetime.now().year
                    if year_int < 1990 or year_int > current_year:
                        return {
                            "valid": False,
                            "message": f"Invalid year: {year}"
                        }
                except ValueError:
                    return {
                        "valid": False,
                        "message": "Invalid year format"
                    }
                
                # Normalize format: XX-DDRRYYYYNNNNNNN
                normalized = f"{state}-{district}{rto}{year}{number}"
                
                return {
                    "valid": True,
                    "normalized": normalized,
                    "components": {
                        "state": state,
                        "district": district,
                        "rto": rto,
                        "year": year,
                        "number": number,
                        "full_rto": f"{district}{rto}"
                    },
                    "message": "Format valid"
                }
        
        return {
            "valid": False,
            "message": "Invalid license format. Expected format: DL-1420230005524"
        }
    
    def verify_license(
        self,
        driver_id: str,
        license_number: str,
        holder_name: Optional[str] = None,
        date_of_birth: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Verify driving license against external API or mark for manual review.
        
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
        format_result = self.validate_format(license_number)
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
                # TODO: Integrate with license verification API
                # Example: Parivahan Sarthi API, DigiLocker
                
                # api_result = self._call_verification_api(
                #     normalized, holder_name, date_of_birth
                # )
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
                "license_number": normalized,
                "components": format_result["components"],
                "holder_name": holder_name,
                "date_of_birth": date_of_birth,
                "reason": "Automatic verification not available. Pending manual review by admin.",
                "verified_at": None,
                "vehicle_classes": []  # To be filled after verification
            }
            
            # Step 4: Update driver record
            update_response = supabase_client.table("drivers").update({
                "license_verification_status": status,
                "license_verification_details": details,
                "license_verified_at": datetime.now().isoformat() if status == "verified" else None
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
                "verification_type": "license",
                "status": "initiated" if status == "manual_review" else status,
                "details": {
                    "driver_id": driver_id,
                    "license_number": normalized,
                    "verification_method": "api" if self.api_available else "manual_review"
                }
            }).execute()
            
            # Step 6: Update account status if needed
            self._update_account_status(driver_id)
            
            message_map = {
                "verified": "Driving license verified successfully!",
                "manual_review": "License submitted for manual verification. Admin will review within 24 hours.",
                "failed": "License verification failed. Please check the license number."
            }
            
            return {
                "status": status,
                "verified": status == "verified",
                "details": details,
                "message": message_map.get(status, "Verification status updated")
            }
            
        except Exception as e:
            print(f"❌ License verification failed: {e}")
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
        """Get license verification status for a driver."""
        if not supabase_client:
            return {"status": "unknown"}
        
        try:
            response = supabase_client.table("drivers").select(
                "license_verification_status, license_verified_at, license_verification_details"
            ).eq("id", driver_id).single().execute()
            
            if response.data:
                return {
                    "status": response.data.get("license_verification_status", "pending"),
                    "verified_at": response.data.get("license_verified_at"),
                    "details": response.data.get("license_verification_details", {})
                }
            
            return {"status": "pending"}
            
        except Exception as e:
            print(f"❌ Failed to get verification status: {e}")
            return {"status": "unknown"}
    
    def check_vehicle_class_compatibility(
        self,
        license_classes: list,
        vehicle_type: str
    ) -> Dict[str, any]:
        """
        Check if license classes are compatible with vehicle type.
        
        Returns:
            dict with 'compatible' and 'message'
        """
        # Map vehicle types to required license classes
        vehicle_class_map = {
            "Mini Truck": ["LMV-TR", "HMV", "HGMV", "MGV", "TRANS"],
            "Standard Truck": ["HMV", "HGMV", "MGV", "TRANS"],
            "Heavy Truck": ["HMV", "HGMV", "TRANS"],
            "Two Wheeler": ["MCWG", "MCWOG"],
            "Three Wheeler": ["LMV", "LMV-TR"]
        }
        
        required_classes = vehicle_class_map.get(vehicle_type, [])
        
        if not required_classes:
            return {
                "compatible": True,
                "message": "Vehicle type not restricted"
            }
        
        # Check if any license class matches required classes
        for lic_class in license_classes:
            if any(req in lic_class for req in required_classes):
                return {
                    "compatible": True,
                    "message": f"License class {lic_class} is valid for {vehicle_type}"
                }
        
        return {
            "compatible": False,
            "message": f"License does not have required class for {vehicle_type}. Required: {', '.join(required_classes)}"
        }
    
    def _call_verification_api(
        self,
        license_number: str,
        holder_name: Optional[str],
        date_of_birth: Optional[str]
    ) -> Dict:
        """
        Call external license verification API.
        TO BE IMPLEMENTED when API credentials are available.
        """
        # Example integration with Parivahan Sarthi or DigiLocker
        # import requests
        # 
        # response = requests.post(
        #     "https://api.example.com/license/verify",
        #     json={
        #         "license_number": license_number,
        #         "name": holder_name,
        #         "dob": date_of_birth
        #     },
        #     headers={"Authorization": f"Bearer {api_key}"}
        # )
        # 
        # if response.status_code == 200:
        #     data = response.json()
        #     return {
        #         "verified": data["verified"],
        #         "details": {
        #             "holder_name": data["name"],
        #             "issue_date": data["issue_date"],
        #             "expiry_date": data["expiry_date"],
        #             "vehicle_classes": data["classes"],
        #             "address": data["address"]
        #         }
        #     }
        
        return {
            "verified": False,
            "error": "API not implemented"
        }


# Singleton instance
license_verification_service = LicenseVerificationService()
