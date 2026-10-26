"""
services/mandi_config.py

Single source of truth for mandi coordinates.
"""

from typing import Optional, Tuple, Dict, Any

MANDI_COORDS: Dict[str, Dict[str, Any]] = {
    # Tamil Nadu Mandis
    "koyambedu mandi":  {"lat": 13.0716, "lng": 80.1945, "name": "Koyambedu Mandi, Chennai"},
    "madurai mandi":    {"lat":  9.9252, "lng": 78.1198, "name": "Madurai Mandi"},
    "coimbatore mandi": {"lat": 11.0168, "lng": 76.9558, "name": "Coimbatore Mandi"},
    "salem mandi":      {"lat": 11.6643, "lng": 78.1460, "name": "Salem Mandi"},
    "trichy mandi":     {"lat": 10.7905, "lng": 78.7047, "name": "Trichy Mandi"},
    "vellore mandi":    {"lat": 12.9165, "lng": 79.1325, "name": "Vellore Mandi"},
    
    # Andhra Pradesh Mandis
    "chittoor mandi":   {"lat": 13.2172, "lng": 79.1003, "name": "Chittoor Mandi, Andhra Pradesh"},
    "tirupati mandi":   {"lat": 13.6288, "lng": 79.4192, "name": "Tirupati Mandi, Andhra Pradesh"},
    "vijayawada mandi": {"lat": 16.5062, "lng": 80.6480, "name": "Vijayawada Mandi, Andhra Pradesh"},
    "visakhapatnam mandi": {"lat": 17.6868, "lng": 83.2185, "name": "Visakhapatnam Mandi, Andhra Pradesh"},
    "guntur mandi":     {"lat": 16.3067, "lng": 80.4365, "name": "Guntur Mandi, Andhra Pradesh"},
    "nellore mandi":    {"lat": 14.4426, "lng": 79.9865, "name": "Nellore Mandi, Andhra Pradesh"},
    "anantapur mandi":  {"lat": 14.6819, "lng": 77.6006, "name": "Anantapur Mandi, Andhra Pradesh"},
    "kadapa mandi":     {"lat": 14.4673, "lng": 78.8242, "name": "Kadapa Mandi, Andhra Pradesh"},
    "kurnool mandi":    {"lat": 15.8281, "lng": 78.0373, "name": "Kurnool Mandi, Andhra Pradesh"},
    
    # Other States
    "delhi mandi":      {"lat": 28.7196, "lng": 77.1724, "name": "Azadpur Mandi, Delhi"},
    "bangalore mandi":  {"lat": 12.9698, "lng": 77.7499, "name": "Yeshwanthpur Mandi, Bangalore"},
    "hyderabad mandi":  {"lat": 17.4513, "lng": 78.3832, "name": "Bowenpally Mandi, Hyderabad"},
}


def get_mandi_coords(destination: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lng) for a known mandi destination string."""
    if not destination:
        return None
    key = destination.strip().lower()
    for k, v in MANDI_COORDS.items():
        if k in key or key in k:
            return v["lat"], v["lng"]
    return None


def get_mandi_info(destination: str) -> Optional[Dict[str, Any]]:
    """Return full mandi metadata dictionary."""
    if not destination:
        return None
    key = destination.strip().lower()
    for k, v in MANDI_COORDS.items():
        if k in key or key in k:
            return v
    return None
