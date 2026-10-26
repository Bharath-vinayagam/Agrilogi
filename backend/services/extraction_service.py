import json
import re

from pydantic import BaseModel, Field

try:
    from groq import Groq as _GroqClient
except ImportError:
    _GroqClient = None

from models.schemas import ExtractionRequest, ExtractionResult
from services.context_service import normalize_crop, normalize_village
from settings import settings

_groq_client = _GroqClient(api_key=settings.groq_api_key) if _GroqClient and settings.groq_api_key else None


NAME_PATTERNS = [
    re.compile(r"\bmy name is\s+([A-Za-z][A-Za-z .'-]{1,40})", re.IGNORECASE),
    re.compile(r"\bi am\s+([A-Za-z][A-Za-z .'-]{1,40})", re.IGNORECASE),
    re.compile(r"\bthis is\s+([A-Za-z][A-Za-z .'-]{1,40})", re.IGNORECASE),
    re.compile(r"\bmain\s+([A-Za-z][A-Za-z .'-]{1,40})", re.IGNORECASE),
    re.compile(r"\bmera naam\s+([A-Za-z][A-Za-z .'-]{1,40})", re.IGNORECASE),
    re.compile(r"\bnaan\s+([A-Za-z][A-Za-z .'-]{1,40})", re.IGNORECASE),
    re.compile(r"\ben peyar\s+([A-Za-z][A-Za-z .'-]{1,40})", re.IGNORECASE),
]

NAME_STOP_WORDS = {
    "from",
    "se",
    "village",
    "gaon",
    "oor",
    "ooru",
    "i",
    "am",
    "hoon",
    "hun",
    "hai",
    "hu",
    "have",
    "has",
    "with",
    "crop",
    "tomato",
    "tomatoes",
    "thakkali",
    "takali",
    "brinjal",
    "baingan",
    "onion",
    "banana",
    "paddy",
    "rice",
    "kg",
    "kilo",
    "kilogram",
    "kilograms",
    "want",
    "transport",
    "send",
    "load",
}


class ConfidenceScores(BaseModel):
    farmer_name: int = Field(description="Confidence score from 0-100.")
    village: int = Field(description="Confidence score from 0-100.")
    crop: int = Field(description="Confidence score from 0-100.")
    weight: int = Field(description="Confidence score from 0-100.")


class ExtractionSchema(BaseModel):
    farmer_name: str
    crop: str
    weight: int
    village: str
    confidence: ConfidenceScores


def extract_from_transcript(payload: ExtractionRequest) -> ExtractionResult:
    if _groq_client:
        return _groq_extraction(payload)
    return _rule_based_extraction(payload)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(",", " ").replace(".", " ")).strip()


def _clean_farmer_name(name: str) -> str:
    words = []
    for raw_word in _normalize_text(name).split():
        word = raw_word.strip(" .,'-")
        if not word or word.lower() in NAME_STOP_WORDS:
            break
        words.append(word)
    if not words:
        return "Unknown Farmer"
    return " ".join(words[:3]).title()


def _extract_name(transcript: str) -> tuple[str, int]:
    normalized = _normalize_text(transcript)
    for pattern in NAME_PATTERNS:
        match = pattern.search(normalized)
        if match:
            name = _clean_farmer_name(match.group(1))
            if name != "Unknown Farmer":
                return name, 92

    titled_words = [
        word.strip(" .,'-")
        for word in normalized.split()
        if word.strip(" .,'-").istitle() and word.lower() not in NAME_STOP_WORDS
    ]
    if titled_words:
        return _clean_farmer_name(titled_words[0]), 76
    return "Unknown Farmer", 45


TAMIL_PHONETIC_WEIGHT_PATTERNS = [
    # Speech-to-Text misrecognition for "naanooru kg" (நானூறு கேஜி):
    (r"நான்\s*ஒரு\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 400, 95),
    (r"நானூறு\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 400, 95),
    (r"நாலு\s*நூறு\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 400, 95),
    (r"\bnaanooru\b", 400, 95),
    (r"நூறு\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 100, 95),
    (r"இருநூறு\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 200, 95),
    (r"முந்நூறு\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 300, 95),
    (r"ஐந்நூறு\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 500, 95),
    (r"அறுநூறு\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 600, 95),
    (r"ஏழுநூறு\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 700, 95),
    (r"எண்ணூறு\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 800, 95),
    (r"தொள்ளாயிரம்\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 900, 95),
    (r"ஆயிரம்\s*(?:கேஜி|கிலோ|கிலோகிராம்|kg)?", 1000, 95),

    # Hindi number words:
    (r"चार\s*सौ\s*(?:किलो|केजी|kg)?", 400, 95),
    (r"दो\s*सौ\s*(?:किलो|केजी|kg)?", 200, 95),
    (r"तीन\s*सौ\s*(?:किलो|केजी|kg)?", 300, 95),
    (r"पांच\s*सौ\s*(?:किलो|केजी|kg)?", 500, 95),
    (r"पाँच\s*सौ\s*(?:किलो|केजी|kg)?", 500, 95),
    (r"एक\s*सौ\s*(?:किलो|केजी|kg)?", 100, 95),
    (r"एक\s*हज़ार\s*(?:किलो|केजी|kg)?", 1000, 95),
]


def _extract_weight(transcript: str) -> tuple[int, int]:
    normalized = transcript.lower().replace(",", " ")

    # Check Tamil and Hindi phonetic and number word patterns first
    for pattern, val, conf in TAMIL_PHONETIC_WEIGHT_PATTERNS:
        if re.search(pattern, transcript, re.IGNORECASE):
            return val, conf

    patterns = [
        # Digits with English/Tamil/Hindi units
        r"(\d{1,5})\s*(?:kg|kgs|kilo|kilos|kilogram|kilograms|கேஜி|கிலோ|கிலோகிராம்|किलो|केजी)",
        # Sacks/bags (50kg per bag)
        r"(\d{1,3})\s*(?:bag|bags|sack|sacks|மூட்டை|மூடை|முட்டை|बोरी|कट्टा|कट्टे)",
        # Context patterns
        r"(?:weight|weighs|have|has|paas|kitta|transport|send|load|crop|அளவு|எடை)\D{0,30}(\d{1,5})",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            value = int(match.group(1))
            if any(b in match.group(0) for b in ["bag", "sack", "மூட்டை", "மூடை", "முட்டை", "बोरी", "कट्टा"]):
                value *= 50
            return value, 96
    return 0, 35


def _extract_locations(transcript: str) -> tuple[str, str]:
    """
    Extracts origin pickup village and destination from transcript.
    Supports English ('from X to Y'), Tamil ('X டு Y' or 'X லிருந்து Y'), and Hindi.
    """
    pickup = "Unknown Village"
    dest = "Koyambedu Mandi"

    # 1. Tamil 'X டு Y' or 'X to Y'
    to_match = re.search(r"([^\s]+)\s+(?:டு|to|நோக்கி)\s+([^\s]+)", transcript, re.IGNORECASE)
    if to_match:
        w1, w2 = to_match.group(1), to_match.group(2)
        v1 = normalize_village(w1)
        v2 = normalize_village(w2)
        if v1 != "Unknown Village":
            pickup = v1
        if v2 != "Unknown Village":
            dest = "Koyambedu Mandi" if v2 in ["Chennai", "Koyambedu Mandi"] else v2

    # 2. 'X ல இருந்து Y' or 'from X to Y'
    from_match = re.search(r"(?:from|இருந்து|லிருந்து|से)\s+([^\s]+)", transcript, re.IGNORECASE)
    if from_match and pickup == "Unknown Village":
        v = normalize_village(from_match.group(1))
        if v != "Unknown Village":
            pickup = v

    # Fallback: scan for any known village
    if pickup == "Unknown Village":
        candidate = normalize_village(transcript)
        if candidate != "Unknown Village" and candidate != "Chennai":
            pickup = candidate

    return pickup, dest


def _confidence_for(value: str, unknown: str, high: int = 92) -> int:
    return high if value != unknown else 48


def _rule_based_extraction(payload: ExtractionRequest) -> ExtractionResult:
    transcript = _normalize_text(payload.transcript)
    farmer_name, farmer_confidence = _extract_name(transcript)
    village, destination = _extract_locations(transcript)
    crop = normalize_crop(transcript)
    weight, weight_confidence = _extract_weight(transcript)

    return ExtractionResult(
        transcript=transcript,
        extracted={
            "farmer_name": farmer_name,
            "village": village,
            "source_village": village,
            "destination": destination,
            "destination_village": destination,
            "crop": crop,
            "weight": weight,
        },
        confidence={
            "farmer_name": farmer_confidence,
            "village": _confidence_for(village, "Unknown Village"),
            "crop": _confidence_for(crop, "Unknown Crop", 95),
            "weight": weight_confidence,
        },
    )


def _groq_extraction(payload: ExtractionRequest) -> ExtractionResult:
    try:
        response = _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract farmer logistics booking details from rural Tamil, Hindi, "
                        "or English transcripts. Return only a JSON object with these fields: "
                        "farmer_name (string), crop (string), weight (integer kg), village (string), "
                        "confidence (object with farmer_name, village, crop, weight as integers 0-100). "
                        "Normalize village and crop spellings."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Transcript: {payload.transcript}",
                },
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        confidence = data.get("confidence", {})
        return ExtractionResult(
            transcript=payload.transcript,
            extracted={
                "farmer_name": _clean_farmer_name(str(data.get("farmer_name", "Unknown Farmer"))),
                "village": str(data.get("village") or normalize_village(payload.transcript)),
                "crop": str(data.get("crop") or normalize_crop(payload.transcript)),
                "weight": int(data.get("weight") or 0),
            },
            confidence={
                "farmer_name": int(confidence.get("farmer_name", 90)),
                "village": int(confidence.get("village", 90)),
                "crop": int(confidence.get("crop", 90)),
                "weight": int(confidence.get("weight", 90)),
            },
        )
    except Exception as exc:
        print(f"Groq extraction failed: {exc}. Falling back to rule-based.")
        return _rule_based_extraction(payload)
