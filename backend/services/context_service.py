VILLAGE_DICTIONARY = {
    # Melma
    "melma": {"canonical": "Melma", "lat": 12.516, "lng": 79.158},
    "melma village": {"canonical": "Melma", "lat": 12.516, "lng": 79.158},
    "melmavur": {"canonical": "Melma", "lat": 12.516, "lng": 79.158},
    "மேல்மா": {"canonical": "Melma", "lat": 12.516, "lng": 79.158},

    # Athur
    "athur": {"canonical": "Athur", "lat": 12.55, "lng": 79.2},
    "attur": {"canonical": "Athur", "lat": 12.55, "lng": 79.2},
    "aathur": {"canonical": "Athur", "lat": 12.55, "lng": 79.2},
    "ஆத்தூர்": {"canonical": "Athur", "lat": 12.55, "lng": 79.2},

    # Sevoor
    "sevoor": {"canonical": "Sevoor", "lat": 12.49, "lng": 79.25},
    "sethur": {"canonical": "Sevoor", "lat": 12.49, "lng": 79.25},
    "sevur": {"canonical": "Sevoor", "lat": 12.49, "lng": 79.25},
    "சேவூர்": {"canonical": "Sevoor", "lat": 12.49, "lng": 79.25},

    # Vallam
    "vallam": {"canonical": "Vallam", "lat": 12.79, "lng": 79.71},
    "வல்லம்": {"canonical": "Vallam", "lat": 12.79, "lng": 79.71},

    # Orikkai
    "orikkai": {"canonical": "Orikkai", "lat": 12.81, "lng": 79.71},
    "ஒரிக்காய்": {"canonical": "Orikkai", "lat": 12.81, "lng": 79.71},

    # Walajabad
    "walajabad": {"canonical": "Walajabad", "lat": 12.79, "lng": 79.82},
    "வாலாஜாபாத்": {"canonical": "Walajabad", "lat": 12.79, "lng": 79.82},

    # Kancheepuram
    "kancheepuram": {"canonical": "Kancheepuram", "lat": 12.83, "lng": 79.70},
    "kanchipuram": {"canonical": "Kancheepuram", "lat": 12.83, "lng": 79.70},
    "காஞ்சிபுரம்": {"canonical": "Kancheepuram", "lat": 12.83, "lng": 79.70},

    # Chittoor
    "chittoor": {"canonical": "Chittoor", "lat": 13.2172, "lng": 79.1003},
    "chittor": {"canonical": "Chittoor", "lat": 13.2172, "lng": 79.1003},
    "சித்தூர்": {"canonical": "Chittoor", "lat": 13.2172, "lng": 79.1003},

    # Chennai / Mandi
    "chennai": {"canonical": "Chennai", "lat": 13.0827, "lng": 80.2707},
    "சென்னை": {"canonical": "Chennai", "lat": 13.0827, "lng": 80.2707},
    "koyambedu": {"canonical": "Koyambedu Mandi", "lat": 13.0694, "lng": 80.1948},
    "கோயம்பேடு": {"canonical": "Koyambedu Mandi", "lat": 13.0694, "lng": 80.1948},
}

CROP_ALIASES = {
    # Tomato
    "tomato": "Tomato",
    "tomatoes": "Tomato",
    "tomatoe": "Tomato",
    "thakkali": "Tomato",
    "takali": "Tomato",
    "தக்காளி": "Tomato",
    "டொமேட்டோ": "Tomato",
    "tamatar": "Tomato",
    "टमाटर": "Tomato",

    # Brinjal
    "brinjal": "Brinjal",
    "eggplant": "Brinjal",
    "kathirikai": "Brinjal",
    "kathari": "Brinjal",
    "கத்திரிக்காய்": "Brinjal",
    "கத்திரி": "Brinjal",
    "baingan": "Brinjal",
    "बैंगन": "Brinjal",

    # Onion
    "onion": "Onion",
    "onions": "Onion",
    "vengayam": "Onion",
    "venkayam": "Onion",
    "வெங்காயம்": "Onion",
    "வெங்காய": "Onion",
    "pyaz": "Onion",
    "pyaaz": "Onion",
    "प्याज": "Onion",

    # Banana
    "banana": "Banana",
    "bananas": "Banana",
    "vazhai": "Banana",
    "vazhaipazham": "Banana",
    "வாழை": "Banana",
    "வாழைப்பழம்": "Banana",
    "kela": "Banana",
    "केला": "Banana",

    # Potato
    "potato": "Potato",
    "potatoes": "Potato",
    "urulai": "Potato",
    "urulaikizhangu": "Potato",
    "உருளைக்கிழங்கு": "Potato",
    "உருளை": "Potato",
    "aloo": "Potato",
    "आलू": "Potato",

    # Paddy / Rice
    "paddy": "Paddy",
    "rice": "Paddy",
    "nellu": "Paddy",
    "நெல்": "Paddy",
    "அரிசி": "Paddy",
    "dhan": "Paddy",
    "chawal": "Paddy",
    "धान": "Paddy",
    "चावल": "Paddy",

    # Cabbage
    "cabbage": "Cabbage",
    "muttakose": "Cabbage",
    "முட்டைக்கோஸ்": "Cabbage",
    "patta gobhi": "Cabbage",
    "पत्ता गोभी": "Cabbage",

    # Mango
    "mango": "Mango",
    "mangoes": "Mango",
    "mambazham": "Mango",
    "மாம்பழம்": "Mango",
    "மாங்காய்": "Mango",
    "aam": "Mango",
    "आम": "Mango",

    # Carrot
    "carrot": "Carrot",
    "கேரட்": "Carrot",
    "gajar": "Carrot",
    "गाजर": "Carrot",
}


def normalize_village(text: str) -> str:
    lowered = text.lower()
    for key, value in VILLAGE_DICTIONARY.items():
        if key in lowered or key in text:
            return str(value["canonical"])
    return "Unknown Village"


def normalize_crop(text: str) -> str:
    lowered = text.lower()
    for alias, crop in CROP_ALIASES.items():
        if alias in lowered or alias in text:
            return crop
    return "Unknown Crop"
