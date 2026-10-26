"""
SMS API Routes for Agrilogi
Handles SMS notification endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.sms_service import (
    send_registration_sms,
    send_login_sms,
    send_driver_assignment_sms,
    send_bundle_created_sms,
    send_trip_update_sms
)

router = APIRouter()


# Request models
class RegistrationSMSRequest(BaseModel):
    name: str
    phone: str
    role: str


class LoginSMSRequest(BaseModel):
    name: str
    phone: str


class DriverAssignmentSMSRequest(BaseModel):
    driver_name: str
    phone: str
    order_id: str


class BundleCreatedSMSRequest(BaseModel):
    farmer_name: str
    phone: str
    bundle_id: str
    savings: int


class TripUpdateSMSRequest(BaseModel):
    user_name: str
    phone: str
    trip_id: str
    status: str


class CustomSMSRequest(BaseModel):
    phone: str
    message: str


# Response model
class SMSResponse(BaseModel):
    success: bool
    message: str


# Endpoints
@router.post("/registration", response_model=SMSResponse)
async def send_registration_notification(request: RegistrationSMSRequest):
    """Send registration success SMS"""
    try:
        success = send_registration_sms(request.name, request.phone, request.role)
        return SMSResponse(
            success=success,
            message="Registration SMS sent successfully" if success else "Failed to send registration SMS"
        )
    except Exception as e:
        print(f"Registration SMS error: {e}")
        # Don't throw error - SMS is non-critical
        return SMSResponse(success=False, message=str(e))


@router.post("/login", response_model=SMSResponse)
async def send_login_notification(request: LoginSMSRequest):
    """Send login alert SMS"""
    try:
        success = send_login_sms(request.name, request.phone)
        return SMSResponse(
            success=success,
            message="Login SMS sent successfully" if success else "Failed to send login SMS"
        )
    except Exception as e:
        print(f"Login SMS error: {e}")
        # Don't throw error - SMS is non-critical
        return SMSResponse(success=False, message=str(e))


@router.post("/driver-assignment", response_model=SMSResponse)
async def send_driver_assignment_notification(request: DriverAssignmentSMSRequest):
    """Send driver assignment SMS"""
    try:
        success = send_driver_assignment_sms(request.driver_name, request.phone, request.order_id)
        return SMSResponse(
            success=success,
            message="Driver assignment SMS sent successfully" if success else "Failed to send assignment SMS"
        )
    except Exception as e:
        print(f"Driver assignment SMS error: {e}")
        return SMSResponse(success=False, message=str(e))


@router.post("/bundle-created", response_model=SMSResponse)
async def send_bundle_created_notification(request: BundleCreatedSMSRequest):
    """Send bundle created SMS"""
    try:
        success = send_bundle_created_sms(
            request.farmer_name,
            request.phone,
            request.bundle_id,
            request.savings
        )
        return SMSResponse(
            success=success,
            message="Bundle SMS sent successfully" if success else "Failed to send bundle SMS"
        )
    except Exception as e:
        print(f"Bundle created SMS error: {e}")
        return SMSResponse(success=False, message=str(e))


@router.post("/trip-update", response_model=SMSResponse)
async def send_trip_update_notification(request: TripUpdateSMSRequest):
    """Send trip update SMS"""
    try:
        success = send_trip_update_sms(
            request.user_name,
            request.phone,
            request.trip_id,
            request.status
        )
        return SMSResponse(
            success=success,
            message="Trip update SMS sent successfully" if success else "Failed to send trip update SMS"
        )
    except Exception as e:
        print(f"Trip update SMS error: {e}")
        return SMSResponse(success=False, message=str(e))


@router.get("/notifications/{phone}")
async def get_notifications_for_phone(phone: str):
    """Get SMS notifications for a specific phone number"""
    try:
        from services.sms_service import sms_service
        from database.db import supabase_client
        if not supabase_client:
            return []
        # Format phone to match how it's stored
        formatted = sms_service._format_phone(phone)
        res = supabase_client.table("notifications")\
            .select("*")\
            .eq("phone", formatted)\
            .eq("channel", "sms")\
            .order("created_at", desc=True)\
            .limit(20)\
            .execute()
        return res.data or []
    except Exception as e:
        print(f"Error fetching notifications: {e}")
        return []



    """Send custom SMS (for testing)"""
    try:
        from services.sms_service import sms_service
        success = sms_service.send_sms(request.phone, request.message, sms_type="custom")
        return SMSResponse(
            success=success,
            message="Custom SMS sent successfully" if success else "Failed to send custom SMS"
        )
    except Exception as e:
        print(f"Custom SMS error: {e}")
        return SMSResponse(success=False, message=str(e))
