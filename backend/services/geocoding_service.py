"""
services/geocoding_service.py

Geocodes a full address string to (lat, lng) using:
  1. Ola Maps Geocoding API — primary (best India/Tamil Nadu accuracy)
  2. Nominatim (OpenStreetMap) — fallback if Ola Maps key not set or fails
  3. context_service.py hardcoded coords — fallback for known villages
  4. None — skip from clustering gracefully

Ola Maps API docs: https://maps.olakrutrim.com/docs/geocoding/geocoding-api
Base URL: https://api.olamaps.io
Auth: ?api_key=YOUR_KEY as query parameter
"""

import time
import urllib.parse
import urllib.request
import json

from services.context_service import VILLAGE_DICTIONARY
from settings import settings

_last_nominatim_call = 0.0


def _ola_maps_geocode(address: str) -> tuple[float, float] | None:
    """Call Ola Maps Geocoding API with Tamil Nadu bounding box validation."""
    if not settings.ola_maps_api_key or not settings.ola_maps_api_key.strip():
        return None

    query = urllib.parse.urlencode({
        "address": address,
        "api_key": settings.ola_maps_api_key.strip(),
    })
    url = f"https://api.olamaps.io/places/v1/geocode?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Agrilogi/1.0",
            "X-Request-Id": "agrilogi-geocode",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())

        results = data.get("geocodingResults", [])
        if results:
            loc = results[0]["geometry"]["location"]
            lat, lng = float(loc["lat"]), float(loc["lng"])

            # Validate result is within India bounding box
            # India: lat 6-37, lng 68-98
            if not (6.0 <= lat <= 37.0 and 68.0 <= lng <= 98.0):
                print(f"Ola Maps returned coordinates outside India ({lat}, {lng}) for '{address}' — rejecting")
                return None

            # If address contains a pincode, do a loose district-level sanity check
            # by verifying the result formatted address shares some words with the input
            formatted = results[0].get("formatted_address", "").lower()
            address_lower = address.lower()

            # Extract pincode from address if present
            import re
            pincode_match = re.search(r'\b(\d{6})\b', address)
            if pincode_match:
                pincode = pincode_match.group(1)
                if pincode not in formatted:
                    print(f"Ola Maps pincode mismatch: input has {pincode} but result '{formatted[:80]}' doesn't — falling back")
                    return None

            return lat, lng
    except Exception as e:
        print(f"Ola Maps geocode failed for '{address}': {e}")

    return None


def _nominatim_geocode(address: str) -> tuple[float, float] | None:
    """Call Nominatim with 1 req/sec rate limit — fallback only."""
    global _last_nominatim_call

    elapsed = time.time() - _last_nominatim_call
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    query = urllib.parse.urlencode({
        "q": address,
        "format": "json",
        "limit": 1,
        "countrycodes": "in",
    })
    url = f"https://nominatim.openstreetmap.org/search?{query}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Agrilogi/1.0 (farm-logistics-demo)"}
    )

    try:
        _last_nominatim_call = time.time()
        with urllib.request.urlopen(req, timeout=5) as resp:
            results = json.loads(resp.read().decode())
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        print(f"Nominatim geocode failed for '{address}': {e}")

    return None


def _hardcoded_coords(address: str) -> tuple[float, float] | None:
    """Scan address for any known village name from context_service."""
    address_lower = address.lower()
    for key, entry in VILLAGE_DICTIONARY.items():
        if key in address_lower or key in address:
            return float(entry["lat"]), float(entry["lng"])
    return None


def _district_fallback(address: str) -> tuple[float, float] | None:
    """
    District-level fallback for major Tamil Nadu cities/districts.
    Returns approximate center coordinates when exact address fails.
    """
    address_lower = address.lower()
    
    # Major Tamil Nadu districts with center coordinates
    DISTRICT_COORDS = {
        "chennai": (13.0827, 80.2707),
        "kanchipuram": (12.8342, 79.7036),
        "tiruvallur": (13.1436, 79.9098),
        "chengalpattu": (12.6919, 79.9758),
        "vellore": (12.9165, 79.1325),
        "tiruvannamalai": (12.2253, 79.0747),
        "villupuram": (11.9401, 79.4861),
        "cuddalore": (11.7480, 79.7714),
        "salem": (11.6643, 78.1460),
        "namakkal": (11.2189, 78.1677),
        "dharmapuri": (12.1211, 78.1582),
        "krishnagiri": (12.5186, 78.2137),
        "erode": (11.3410, 77.7172),
        "coimbatore": (11.0168, 76.9558),
        "tiruppur": (11.1085, 77.3411),
        "nilgiris": (11.4102, 76.6950),
        "karur": (10.9601, 78.0766),
        "tiruchirappalli": (10.7905, 78.7047),
        "trichy": (10.7905, 78.7047),
        "perambalur": (11.2324, 78.8798),
        "ariyalur": (11.1401, 79.0782),
        "thanjavur": (10.7870, 79.1378),
        "tiruvarur": (10.7729, 79.6345),
        "nagapattinam": (10.7672, 79.8449),
        "pudukkottai": (10.3833, 78.8000),
        "madurai": (9.9252, 78.1198),
        "theni": (10.0104, 77.4977),
        "dindigul": (10.3673, 77.9803),
        "ramanathapuram": (9.3639, 78.8377),
        "virudhunagar": (9.5810, 77.9624),
        "sivaganga": (9.8433, 78.4809),
        "thoothukudi": (8.7642, 78.1348),
        "tuticorin": (8.7642, 78.1348),
        "tirunelveli": (8.7139, 77.7567),
        "kanyakumari": (8.0883, 77.5385),
        "tenkasi": (8.9600, 77.3152),
    }
    
    for district, coords in DISTRICT_COORDS.items():
        if district in address_lower:
            print(f"   Using district-level coordinates for '{district}'")
            return coords
    
    return None


def geocode_address(address: str) -> tuple[float | None, float | None]:
    """
    Returns (lat, lng) for a full address string.

    Fallback chain:
      1. Ola Maps API (primary — best India accuracy)
      2. Nominatim simplified (strips street, retries with village+district+pincode)
      3. Hardcoded village dictionary
      4. District-level fallback (major cities)
      5. (None, None) — order excluded from spatial clustering

    Usage:
        lat, lng = geocode_address("12/4 Gandhi Street, Melma, Kanchipuram, Tamil Nadu 631501")
    """
    if not address or address.strip().lower() in ("unknown village", ""):
        print(f"⚠️ Empty or unknown address provided")
        return None, None

    print(f"🔍 Geocoding address: '{address}'")

    # 1. Ola Maps — full address
    coords = _ola_maps_geocode(address)
    if coords:
        print(f"✅ Geocoded via Ola Maps: {coords}")
        return coords

    # 2a. Nominatim — full address
    coords = _nominatim_geocode(f"{address}, Tamil Nadu, India")
    if coords:
        print(f"✅ Geocoded via Nominatim (full): {coords}")
        return coords

    # 2b. Nominatim — simplified (last 3 comma parts, strips street number)
    parts = [p.strip() for p in address.split(",")]
    if len(parts) > 2:
        simplified = ", ".join(parts[-3:])
        coords = _nominatim_geocode(f"{simplified}, Tamil Nadu, India")
        if coords:
            print(f"✅ Geocoded via Nominatim (simplified '{simplified}'): {coords}")
            return coords

    # 3. Hardcoded village dictionary
    coords = _hardcoded_coords(address)
    if coords:
        print(f"✅ Geocoded via hardcoded dict: {coords}")
        return coords

    # 4. District-level fallback for major cities/districts
    coords = _district_fallback(address)
    if coords:
        print(f"✅ Geocoded via district-level fallback: {coords}")
        return coords

    print(f"❌ Could not geocode '{address}' — will use fallback rate (₹9/kg)")
    return None, None


# Keep old name as alias so nothing else breaks
geocode_village = geocode_address
