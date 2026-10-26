"""
services/destination_service.py

Normalizes destination strings so minor variations like
"Koyambedu Mandi" vs "Koyambedu Mandi, Chennai" resolve to the same key.

Strategy:
  1. Lowercase + strip
  2. Remove common suffixes/noise words
  3. Match against known market aliases
  4. Fall back to cleaned string
"""

import re

# Known market canonical names and their aliases
MARKET_ALIASES: dict[str, list[str]] = {
    "Koyambedu Mandi": [
        "koyambedu", "koyambedu mandi", "koyambedu market",
        "koyambedu mandi, chennai", "koyambedu mandi chennai",
        "koyambedu vegetable market", "cmda market koyambedu",
        "chennai", "சென்னை", "கோயம்பேடு", "கோயம்பேடு மார்க்கெட்", "கோயம்பேடு மண்டி",
    ],
    "Madurai Mandi": [
        "madurai mandi", "madurai market", "madurai vegetable market",
        "madurai mandi, madurai", "mattuthavani",
    ],
    "Coimbatore Mandi": [
        "coimbatore mandi", "coimbatore market", "mettupalayam market",
        "coimbatore vegetable market",
    ],
    "Salem Mandi": [
        "salem mandi", "salem market", "salem vegetable market",
    ],
    "Trichy Mandi": [
        "trichy mandi", "tiruchirappalli mandi", "trichy market",
        "trichy vegetable market",
    ],
    "Vellore Mandi": [
        "vellore mandi", "vellore market",
    ],
    "Delhi Mandi": [
        "delhi mandi", "azadpur mandi", "delhi market", "new delhi mandi",
    ],
}

# Build reverse lookup: alias → canonical
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in MARKET_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias.lower().strip()] = canonical


def normalize_destination(destination: str) -> str:
    """
    Returns a canonical destination name.

    Examples:
      "Koyambedu Mandi, Chennai" → "Koyambedu Mandi"
      "koyambedu" → "Koyambedu Mandi"
      "Some Unknown Market" → "Some Unknown Market"  (unchanged)
    """
    if not destination:
        return destination

    cleaned = destination.strip()
    key = cleaned.lower()

    # Exact alias match
    if key in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[key]

    # Partial match — check if any alias is contained in the input
    for alias, canonical in _ALIAS_TO_CANONICAL.items():
        if alias in key:
            return canonical

    # No match — return cleaned original with title case
    return cleaned
