"""
Authentication API routes with OTP verification, vehicle verification, and license verification.
Implements secure registration, login, and verification workflows.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, validator
from typing import Optional
import re
from database.db import supabase_client
from services.otp_service import otp_service
from services.vehicle_verification_service import vehicle_verification_service
from services.license_verification_service import license_verification_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SendOTPRequest(BaseModel):
    user_id: str
    phone: str
    name: Optional[str] = None

class VerifyOTPRequest(BaseModel):
    user_id: str
    otp: str
    phone: Optional[str] = None

class RegisterRequest(BaseModel):
    name: str
    phone: str
    password: str
    role: str
    
    # Location fields
    village: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    
    # Farmer specific
    preferred_language: Optional[str] = "en"
    
    # Driver specific
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    license_number: Optional[str] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        # Basic phone validation - at least 10 digits
        digits = re.sub(r'\D', '', v)
        if len(digits) < 10:
            raise ValueError('Phone number must contain at least 10 digits')
        return v
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['farmer', 'driver']:
            raise ValueError('Role must be farmer or driver')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        # Check for at least one number or special character
        if not re.search(r'[\d!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one number or special character')
        return v

class VerifyVehicleRequest(BaseModel):
    driver_id: str
    vehicle_number: str
    owner_name: Optional[str] = None

class VerifyLicenseRequest(BaseModel):
    driver_id: str
    license_number: str
    holder_name: Optional[str] = None
    date_of_birth: Optional[str] = None

class LoginRequest(BaseModel):
    phone: str
    password: str
    role: str


# ============================================================================
# OTP Endpoints
# ============================================================================

@router.post("/send-otp")
async def send_otp(request: SendOTPRequest, http_request: Request):
    """
    Send OTP to user's phone number for verification.
    Rate limited: 60 seconds between requests, 10 per day.
    """
    try:
        # Validate user exists
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not available")
        
        user_response = supabase_client.table("users").select("id, phone, phone_verified").eq(
            "id", request.user_id
        ).single().execute()
        
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already verified
        if user_response.data.get("phone_verified"):
            return {
                "success": True,
                "message": "Phone already verified",
                "already_verified": True
            }
        
        # Send OTP
        result = otp_service.send_otp(
            user_id=request.user_id,
            phone=request.phone,
            name=request.name
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Send OTP endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send OTP")


@router.post("/verify-otp")
async def verify_otp(request: VerifyOTPRequest):
    """
    Verify OTP code provided by user.
    Max 3 attempts per OTP. OTP expires after 5 minutes.
    """
    try:
        result = otp_service.verify_otp(
            user_id=request.user_id,
            otp=request.otp,
            phone=request.phone
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Verify OTP endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Verification failed")


@router.get("/verification-status/{user_id}")
async def get_verification_status(user_id: str):
    """Get phone verification status for a user."""
    try:
        result = otp_service.check_verification_status(user_id)
        return result
        
    except Exception as e:
        print(f"❌ Get verification status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")


# ============================================================================
# Registration Endpoint
# ============================================================================

@router.post("/register")
async def register(request: RegisterRequest, http_request: Request):
    """
    Register new user account.
    Phone verification is required before account can be fully activated.
    """
    try:
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not available")
        
        # Check if phone already exists in users table
        existing_user = supabase_client.table("users").select("id").eq(
            "phone", request.phone
        ).execute()
        
        if existing_user.data:
            raise HTTPException(
                status_code=409,
                detail="Phone number already registered. Please login instead."
            )
        
        # Clean phone number for email mapping
        digits_only = re.sub(r'\D', '', request.phone)
        clean_phone = digits_only[-10:]
        email = f"user{clean_phone}@agrilogi.com"
        
        # Create auth user with Supabase
        try:
            auth_response = supabase_client.auth.sign_up({
                "email": email,
                "password": request.password
            })
        except Exception as auth_error:
            # If auth user already exists but not in our users table, 
            # it's an orphaned record - give helpful error
            error_msg = str(auth_error)
            if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"Account conflict detected. Please contact support or try a different phone number. (Email: {email})"
                )
            raise HTTPException(
                status_code=500,
                detail=f"Authentication error: {error_msg}"
            )
        
        if not auth_response or not hasattr(auth_response, 'user') or not auth_response.user:
            raise HTTPException(
                status_code=500,
                detail="Failed to create authentication user"
            )
        
        user_id = auth_response.user.id
        
        # Insert into users table
        user_data = {
            "id": user_id,
            "name": request.name,
            "phone": request.phone,
            "village": request.village or request.city,  # Backward compatibility
            "city": request.city,
            "district": request.district,
            "state": request.state,
            "pin_code": request.pin_code,
            "preferred_language": request.preferred_language if request.role == "farmer" else "en",
            "role": request.role,
            "phone_verified": False  # Requires OTP verification
        }
        
        user_insert = supabase_client.table("users").insert(user_data).execute()
        
        if not user_insert.data:
            raise HTTPException(status_code=500, detail="Failed to create user record")
        
        # Role-specific table inserts
        if request.role == "farmer":
            farmer_data = {
                "user_id": user_id,
                "village": request.village or request.city,
                "preferred_language": request.preferred_language
            }
            supabase_client.table("farmers").insert(farmer_data).execute()
            
        elif request.role == "driver":
            # Validate driver-specific fields
            if not request.vehicle_number or not request.vehicle_type or not request.license_number:
                raise HTTPException(
                    status_code=400,
                    detail="Driver registration requires vehicle number, type, and license number"
                )
            
            driver_data = {
                "user_id": user_id,
                "vehicle_number": request.vehicle_number,
                "vehicle_type": request.vehicle_type,
                "license_number": request.license_number,
                "city": request.city,
                "district": request.district,
                "state": request.state,
                "pin_code": request.pin_code,
                "reliability_score": 90,
                "completed_trips": 0,
                "rating": 4.5,
                "vehicle_verification_status": "pending",
                "license_verification_status": "pending",
                "account_status": "pending_verification"
            }
            
            driver_insert = supabase_client.table("drivers").insert(
                driver_data
            ).select().execute()
            
            if not driver_insert.data:
                raise HTTPException(status_code=500, detail="Failed to create driver record")
            
            driver_id = driver_insert.data[0]["id"]
            
            # Determine vehicle capacity
            capacity_kg = 1100  # Default: Standard
            v_lower = request.vehicle_type.lower()
            if "mini" in v_lower or "500" in v_lower:
                capacity_kg = 500
            elif "heavy" in v_lower or "2500" in v_lower:
                capacity_kg = 2500
            
            # Insert vehicle record
            vehicle_data = {
                "driver_id": driver_id,
                "vehicle_number": request.vehicle_number,
                "vehicle_type": request.vehicle_type,
                "capacity_kg": capacity_kg
            }
            supabase_client.table("vehicles").insert(vehicle_data).execute()
        
        # Send OTP for phone verification
        otp_result = otp_service.send_otp(
            user_id=user_id,
            phone=request.phone,
            name=request.name
        )
        
        return {
            "success": True,
            "message": "Registration successful. Please verify your phone number with the OTP sent.",
            "user_id": user_id,
            "phone_verified": False,
            "otp_sent": otp_result.get("success", False),
            "otp": otp_result.get("otp") if request.role == "driver" else None,  # Dev mode only
            "requires_verification": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Registration error: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


# ============================================================================
# Login Endpoint
# ============================================================================

@router.post("/login")
async def login(request: LoginRequest):
    """
    Login with phone number and password.
    Returns user profile and verification status.
    """
    try:
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not available")
        
        # Clean phone for email mapping
        digits_only = re.sub(r'\D', '', request.phone)
        clean_phone = digits_only[-10:]
        email = f"user{clean_phone}@agrilogi.com"
        
        # Authenticate with Supabase
        auth_response = supabase_client.auth.sign_in_with_password({
            "email": email,
            "password": request.password
        })
        
        if not auth_response or not hasattr(auth_response, 'session') or not auth_response.session:
            raise HTTPException(
                status_code=401,
                detail="Invalid phone number or password"
            )
        
        session = auth_response.session
        user_id = session.user.id
        
        # Get user profile
        user_response = supabase_client.table("users").select(
            "*"
        ).eq("id", user_id).single().execute()
        
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        user_data = user_response.data
        
        # Verify role matches
        if user_data["role"] != "admin" and user_data["role"] != request.role:
            raise HTTPException(
                status_code=403,
                detail=f"Role mismatch. Your account is registered as {user_data['role'].upper()}"
            )
        
        # Get role-specific data
        additional_data = {}
        
        if user_data["role"] == "driver":
            driver_response = supabase_client.table("drivers").select(
                "*"
            ).eq("user_id", user_id).single().execute()
            
            if driver_response.data:
                additional_data = {
                    "driver_id": driver_response.data["id"],
                    "vehicle_number": driver_response.data["vehicle_number"],
                    "vehicle_type": driver_response.data["vehicle_type"],
                    "license_number": driver_response.data["license_number"],
                    "vehicle_verification_status": driver_response.data.get("vehicle_verification_status"),
                    "license_verification_status": driver_response.data.get("license_verification_status"),
                    "account_status": driver_response.data.get("account_status"),
                    "reliability_score": driver_response.data.get("reliability_score"),
                    "completed_trips": driver_response.data.get("completed_trips"),
                    "rating": driver_response.data.get("rating")
                }
        
        return {
            "success": True,
            "message": "Login successful",
            "user": {
                **user_data,
                **additional_data
            },
            "session": {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_at": session.expires_at
            },
            "phone_verified": user_data.get("phone_verified", False),
            "verification_required": not user_data.get("phone_verified", False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


# ============================================================================
# Vehicle Verification Endpoints
# ============================================================================

@router.post("/verify-vehicle")
async def verify_vehicle(request: VerifyVehicleRequest):
    """
    Initiate vehicle registration verification.
    Validates format and submits for verification (API or manual review).
    """
    try:
        result = vehicle_verification_service.verify_vehicle(
            driver_id=request.driver_id,
            vehicle_number=request.vehicle_number,
            owner_name=request.owner_name
        )
        
        if not result["verified"] and result["status"] == "failed":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Vehicle verification error: {e}")
        raise HTTPException(status_code=500, detail="Vehicle verification failed")


@router.get("/vehicle-status/{driver_id}")
async def get_vehicle_status(driver_id: str):
    """Get vehicle verification status for a driver."""
    try:
        result = vehicle_verification_service.get_verification_status(driver_id)
        return result
        
    except Exception as e:
        print(f"❌ Get vehicle status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")


# ============================================================================
# License Verification Endpoints
# ============================================================================

@router.post("/verify-license")
async def verify_license(request: VerifyLicenseRequest):
    """
    Initiate driving license verification.
    Validates format and submits for verification (API or manual review).
    """
    try:
        result = license_verification_service.verify_license(
            driver_id=request.driver_id,
            license_number=request.license_number,
            holder_name=request.holder_name,
            date_of_birth=request.date_of_birth
        )
        
        if not result["verified"] and result["status"] == "failed":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ License verification error: {e}")
        raise HTTPException(status_code=500, detail="License verification failed")


@router.get("/license-status/{driver_id}")
async def get_license_status(driver_id: str):
    """Get license verification status for a driver."""
    try:
        result = license_verification_service.get_verification_status(driver_id)
        return result
        
    except Exception as e:
        print(f"❌ Get license status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")


# ============================================================================
# Account Status Endpoint
# ============================================================================

@router.get("/account-status/{user_id}")
async def get_account_status(user_id: str):
    """
    Get complete account verification status including phone, vehicle, and license.
    """
    try:
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not available")
        
        # Get user data
        user_response = supabase_client.table("users").select(
            "id, role, phone_verified, phone_verified_at"
        ).eq("id", user_id).single().execute()
        
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_response.data
        status = {
            "user_id": user_id,
            "role": user_data["role"],
            "phone_verified": user_data.get("phone_verified", False),
            "phone_verified_at": user_data.get("phone_verified_at")
        }
        
        # If driver, get vehicle and license status
        if user_data["role"] == "driver":
            driver_response = supabase_client.table("drivers").select(
                "id, vehicle_verification_status, license_verification_status, account_status"
            ).eq("user_id", user_id).single().execute()
            
            if driver_response.data:
                status.update({
                    "driver_id": driver_response.data["id"],
                    "vehicle_verification_status": driver_response.data.get("vehicle_verification_status"),
                    "license_verification_status": driver_response.data.get("license_verification_status"),
                    "account_status": driver_response.data.get("account_status"),
                    "can_accept_loads": (
                        user_data.get("phone_verified", False) and
                        driver_response.data.get("vehicle_verification_status") == "verified" and
                        driver_response.data.get("license_verification_status") == "verified"
                    )
                })
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Get account status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get account status")
