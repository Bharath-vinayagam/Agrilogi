"""
SMS Service for Agrilogi
Handles SMS notifications for registration, login, and other events
"""

import os
from typing import Optional, List, Dict
from datetime import datetime

# Twilio imports (optional - graceful fallback if not available)
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

from database.db import supabase_client


class SMSService:
    """Lightweight SMS service for Agrilogi"""

    def __init__(self):
        self.twilio_available = TWILIO_AVAILABLE
        self.twilio_client = None
        self.twilio_phone = None

        if self.twilio_available:
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            self.twilio_phone = os.getenv("TWILIO_PHONE_NUMBER", "+14155552671")

            if account_sid and auth_token:
                try:
                    self.twilio_client = Client(account_sid, auth_token)
                except Exception as e:
                    print(f"Failed to initialize Twilio client: {e}")

    def send_sms(self, phone: str, message: str, sms_type: str = "notification") -> bool:
        """
        Send SMS to phone number.
        Falls back to DB logging if Twilio is not configured.
        """
        try:
            formatted_phone = self._format_phone(phone)
            if not formatted_phone:
                print(f"Invalid phone number: {phone}")
                return False

            if self.twilio_client:
                return self._send_via_twilio(formatted_phone, message, sms_type)

            return self._log_sms_to_db(formatted_phone, message, sms_type)

        except Exception as e:
            print(f"SMS send error: {e}")
            return False

    def _send_via_twilio(self, phone: str, message: str, sms_type: str) -> bool:
        try:
            msg = self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_phone,
                to=phone
            )
            print(f"SMS sent via Twilio: {msg.sid}")
            self._log_sms_to_db(phone, message, sms_type, status="sent", sms_id=msg.sid)
            return True
        except Exception as e:
            print(f"Twilio send failed: {e}")
            self._log_sms_to_db(phone, message, sms_type, status="failed")
            return False

    def _log_sms_to_db(self, phone: str, message: str, sms_type: str, status: str = "queued", sms_id: Optional[str] = None) -> bool:
        try:
            if not supabase_client:
                print("Supabase client not available for SMS logging")
                return False

            supabase_client.table("notifications").insert({
                "phone": phone,
                "channel": "sms",
                "message": message,
                "status": status,
                "type": sms_type,
            }).execute()

            print(f"SMS logged to database: {phone} ({sms_type})")
            return True
        except Exception as e:
            print(f"Failed to log SMS to database: {e}")
            return False

    def _format_phone(self, phone: str) -> Optional[str]:
        try:
            clean = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if clean.startswith("91"):
                return f"+{clean}"
            elif clean.startswith("+91"):
                return clean
            elif len(clean) == 10 and clean.isdigit():
                return f"+91{clean}"
            else:
                return f"+{clean}" if not clean.startswith("+") else clean
        except Exception as e:
            print(f"Phone formatting error: {e}")
            return None

    # ── Existing notification methods ─────────────────────────────────────

    def send_registration_sms(self, name: str, phone: str, role: str) -> bool:
        message = (
            f"Agrilogi Registration Successful\n\n"
            f"Welcome, {name}.\n\n"
            f"Your account has been created successfully.\n"
            f"Role: {role.capitalize()}\n\n"
            f"You can now access the Agrilogi platform."
        )
        return self.send_sms(phone, message, sms_type="registration")

    def send_login_sms(self, name: str, phone: str) -> bool:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = (
            f"Agrilogi Login Alert\n\n"
            f"Hello {name},\n\n"
            f"You have successfully logged into your Agrilogi account.\n"
            f"Date & Time: {current_time}\n\n"
            f"If this was not you, contact support immediately."
        )
        return self.send_sms(phone, message, sms_type="login")

    def send_driver_assignment_sms(self, driver_name: str, phone: str, order_id: str) -> bool:
        message = (
            f"Agrilogi Order Assignment\n\n"
            f"Hi {driver_name},\n\n"
            f"You have been assigned to deliver order {order_id}.\n"
            f"Check your app for details."
        )
        return self.send_sms(phone, message, sms_type="assignment")

    def send_bundle_created_sms(self, farmer_name: str, phone: str, bundle_id: str, savings: int) -> bool:
        message = (
            f"Agrilogi Bundle Created\n\n"
            f"Hi {farmer_name},\n\n"
            f"Your items have been bundled for delivery!\n"
            f"Bundle ID: {bundle_id}\n"
            f"Estimated Savings: ₹{savings}\n\n"
            f"Check your app for more details."
        )
        return self.send_sms(phone, message, sms_type="bundle_created")

    def send_trip_update_sms(self, user_name: str, phone: str, trip_id: str, status: str) -> bool:
        message = (
            f"Agrilogi Trip Update\n\n"
            f"Hi {user_name},\n\n"
            f"Trip {trip_id} status: {status}\n"
            f"Check your app for real-time tracking."
        )
        return self.send_sms(phone, message, sms_type="trip_update")

    # ── New cluster / bid notification methods ────────────────────────────

    def notify_drivers_cluster_created(self, cluster_ids: List[str]) -> Dict:
        """
        Scenario 1: Notify ALL drivers when new clusters are ready for bidding.
        Triggered after clustering algorithm runs.
        """
        print(f"\n📱 [SMS] Notifying drivers — clusters created: {cluster_ids}")
        try:
            # Fetch cluster details
            clusters_res = supabase_client.table("bundles").select("*").in_("id", cluster_ids).execute()
            clusters = clusters_res.data or []

            total_weight = sum(c.get("total_weight_kg", 0) for c in clusters)
            destinations = list(set(c.get("destination", "Mandi") for c in clusters))
            dest_text = destinations[0].split(",")[0] if len(destinations) == 1 else f"{len(destinations)} locations"

            message = (
                f"Agrilogi: New Loads Available!\n\n"
                f"{len(cluster_ids)} bundle(s) ready for bidding\n"
                f"Total: {total_weight}kg\n"
                f"Destination: {dest_text}\n\n"
                f"Login to place your bid now!"
            )

            # Fetch all drivers
            drivers_res = supabase_client.table("users").select("name, phone").eq("role", "driver").execute()
            drivers = drivers_res.data or []

            sent, failed = 0, 0
            for d in drivers:
                phone = d.get("phone", "")
                if not phone:
                    failed += 1
                    continue
                ok = self.send_sms(phone, message, sms_type="cluster_created")
                if ok:
                    sent += 1
                    print(f"  ✅ Notified driver {d.get('name')} ({phone})")
                else:
                    failed += 1
                    print(f"  ❌ Failed driver {d.get('name')} ({phone})")

            print(f"📊 Cluster SMS — sent: {sent}, failed: {failed}")
            return {"success": True, "drivers_notified": len(drivers), "sms_sent": sent, "sms_failed": failed}

        except Exception as e:
            print(f"❌ notify_drivers_cluster_created error: {e}")
            return {"success": False, "error": str(e), "sms_sent": 0, "sms_failed": 0}

    def notify_bid_winner(self, cluster_id: str, driver_name: str, driver_phone: str, bid_amount: int) -> Dict:
        """
        Scenario 2: Notify winning driver + all farmers when bidding closes.
        Triggered after close_cluster_bidding() assigns a winner.
        """
        print(f"\n📱 [SMS] Notifying bid winner — cluster: {cluster_id}, driver: {driver_name}")
        try:
            # Fetch farmers in cluster
            orders_res = supabase_client.table("orders")\
                .select("id, farmer_name, phone, shared_cost, final_cost, pickup_date, pickup_slot")\
                .eq("cluster_id", cluster_id)\
                .execute()
            farmers = orders_res.data or []

            sent, failed = 0, 0

            # 1. Notify winning driver
            driver_msg = (
                f"Congratulations! You Won!\n\n"
                f"Bundle: {cluster_id}\n"
                f"Amount: Rs{bid_amount}\n"
                f"Pickups: {len(farmers)} farmers\n\n"
                f"Check app for farmer details and pickup locations."
            )
            if driver_phone:
                ok = self.send_sms(driver_phone, driver_msg, sms_type="bid_winner")
                if ok:
                    sent += 1
                    print(f"  ✅ Notified driver {driver_name}")
                else:
                    failed += 1
                    print(f"  ❌ Failed to notify driver {driver_name}")

            # 2. Notify each farmer
            for farmer in farmers:
                farmer_phone = farmer.get("phone", "")
                farmer_name = farmer.get("farmer_name", "Farmer")
                order_id = farmer.get("id", "")
                amount = farmer.get("final_cost") or farmer.get("shared_cost") or 0

                # Build pickup time string
                pickup_date = farmer.get("pickup_date", "")
                pickup_slot = farmer.get("pickup_slot", "")
                pickup_time = f"{pickup_date} {pickup_slot}".strip() or "Tomorrow morning"

                if not farmer_phone:
                    failed += 1
                    continue

                farmer_msg = (
                    f"Driver Assigned - {farmer_name}\n\n"
                    f"Order: {order_id}\n"
                    f"Driver: {driver_name}\n"
                    f"Contact: {driver_phone}\n"
                    f"Pickup: {pickup_time}\n\n"
                    f"Driver will call before pickup.\n"
                    f"Keep your produce ready!"
                )
                ok = self.send_sms(farmer_phone, farmer_msg, sms_type="driver_assigned")
                if ok:
                    sent += 1
                    print(f"  ✅ Notified farmer {farmer_name} ({farmer_phone})")
                else:
                    failed += 1
                    print(f"  ❌ Failed farmer {farmer_name} ({farmer_phone})")

            farmers_notified = len([f for f in farmers if f.get("phone")])
            print(f"📊 Bid Winner SMS — sent: {sent}, failed: {failed}")
            return {
                "success": True,
                "driver_notified": bool(driver_phone),
                "farmers_notified": farmers_notified,
                "sms_sent": sent,
                "sms_failed": failed,
            }

        except Exception as e:
            print(f"❌ notify_bid_winner error: {e}")
            return {"success": False, "error": str(e), "sms_sent": 0, "sms_failed": 0}


# Global SMS service instance
sms_service = SMSService()


# ── Export helpers ─────────────────────────────────────────────────────────────

def send_registration_sms(name: str, phone: str, role: str) -> bool:
    return sms_service.send_registration_sms(name, phone, role)

def send_login_sms(name: str, phone: str) -> bool:
    return sms_service.send_login_sms(name, phone)

def send_driver_assignment_sms(driver_name: str, phone: str, order_id: str) -> bool:
    return sms_service.send_driver_assignment_sms(driver_name, phone, order_id)

def send_bundle_created_sms(farmer_name: str, phone: str, bundle_id: str, savings: int) -> bool:
    return sms_service.send_bundle_created_sms(farmer_name, phone, bundle_id, savings)

def send_trip_update_sms(user_name: str, phone: str, trip_id: str, status: str) -> bool:
    return sms_service.send_trip_update_sms(user_name, phone, trip_id, status)

