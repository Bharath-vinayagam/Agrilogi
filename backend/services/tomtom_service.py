"""
TomTom Matrix Routing v2 Service.
Traffic config: departAt=now, traffic=live, travelMode=truck.
Returns travelTimeInSeconds used as OR-Tools optimization objective.
"""

import os
import requests
from typing import List, Dict
from settings import settings

TOMTOM_BASE_URL        = "https://api.tomtom.com"
TOMTOM_MATRIX_ENDPOINT = "/routing/matrix/2"
TOMTOM_TIMEOUT         = int(os.getenv("TOMTOM_TIMEOUT_SECONDS", "30"))


class TomTomError(Exception):
    pass


class TomTomKeyMissingError(TomTomError):
    pass


def _get_api_key() -> str:
    # Read from pydantic settings (which loads .env correctly)
    key = getattr(settings, "tomtom_api_key", "").strip()
    if not key:
        # fallback to os.getenv directly
        key = os.getenv("TOMTOM_API_KEY", "").strip()
    if not key:
        raise TomTomKeyMissingError(
            "TOMTOM_API_KEY is not set. Add it to backend/.env: TOMTOM_API_KEY=your_key_here"
        )
    return key


def get_fallback_travel_time_matrix(locations: List[Dict]) -> Dict:
    """Fallback n×n distance and travel time matrix when TOMTOM_API_KEY is not configured."""
    import math
    n = len(locations)
    durations = [[0.0] * n for _ in range(n)]
    distances = [[0.0] * n for _ in range(n)]
    traffic_delays = [[0.0] * n for _ in range(n)]

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        return R * 2 * math.asin(math.sqrt(a))

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            dist_km = haversine(locations[i]["latitude"], locations[i]["longitude"], locations[j]["latitude"], locations[j]["longitude"]) * 1.25
            dist_m = dist_km * 1000.0
            # Average commercial truck speed ~40 km/h = 11.11 m/s
            dur_s = (dist_km / 40.0) * 3600.0
            distances[i][j] = round(dist_m, 1)
            durations[i][j] = round(dur_s, 1)
            traffic_delays[i][j] = round(dur_s * 0.1, 1)

    return {"durations": durations, "distances": distances, "traffic_delays": traffic_delays}


def get_travel_time_matrix(locations: List[Dict]) -> Dict:
    """
    Call TomTom Matrix Routing v2 for a full n×n matrix.
    Returns durations (travelTimeInSeconds), distances (lengthInMeters),
    and traffic_delays (trafficDelayInSeconds).
    Falls back to high-accuracy road estimate if TOMTOM_API_KEY is not configured.
    """
    if not locations:
        raise TomTomError("No locations provided.")

    try:
        api_key = _get_api_key()
    except TomTomKeyMissingError:
        print("[TomTom Service] TOMTOM_API_KEY missing - using road fallback matrix.")
        return get_fallback_travel_time_matrix(locations)

    n       = len(locations)
    points  = [{"point": {"latitude": loc["latitude"], "longitude": loc["longitude"]}}
               for loc in locations]

    body = {
        "origins":      points,
        "destinations": points,
        "options": {
            "departAt":          "now",
            "traffic":           "live",
            "travelMode":        "truck",
            "routeType":         "fastest",
            "vehicleCommercial": True,
        },
    }

    url    = f"{TOMTOM_BASE_URL}{TOMTOM_MATRIX_ENDPOINT}"
    params = {"key": api_key}

    try:
        response = requests.post(url, json=body, params=params,
                                 headers={"Content-Type": "application/json"},
                                 timeout=TOMTOM_TIMEOUT)
    except requests.exceptions.ConnectionError as exc:
        raise TomTomError(f"TomTom network connection failed: {exc}") from exc
    except requests.exceptions.Timeout:
        raise TomTomError(f"TomTom request timed out after {TOMTOM_TIMEOUT} seconds.")
    except requests.exceptions.RequestException as exc:
        raise TomTomError(f"TomTom request error: {exc}") from exc

    if response.status_code == 403:
        raise TomTomError("TomTom returned 403 Forbidden. Check TOMTOM_API_KEY.")
    if response.status_code == 429:
        raise TomTomError("TomTom returned 429 Too Many Requests.")
    if response.status_code != 200:
        raise TomTomError(f"TomTom returned HTTP {response.status_code}: {response.text[:200]}")

    data  = response.json()
    cells = data.get("data")
    if cells is None:
        raise TomTomError("TomTom response missing 'data' field.")

    stats = data.get("statistics", {})
    if stats.get("failures", 0) > 0:
        raise TomTomError(f"TomTom returned {stats['failures']} failed cell(s).")

    durations      = [[0.0] * n for _ in range(n)]
    distances      = [[0.0] * n for _ in range(n)]
    traffic_delays = [[0.0] * n for _ in range(n)]

    for cell in cells:
        i = cell["originIndex"]
        j = cell["destinationIndex"]
        summary = cell.get("routeSummary", {})
        durations[i][j]      = float(summary.get("travelTimeInSeconds", 0))
        distances[i][j]      = float(summary.get("lengthInMeters", 0))
        traffic_delays[i][j] = float(summary.get("trafficDelayInSeconds", 0))

    return {"durations": durations, "distances": distances, "traffic_delays": traffic_delays}
