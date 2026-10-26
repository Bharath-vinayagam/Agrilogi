"""
Generate ALL Audio Files for Agrilogi Voice Assistant
Includes initial prompts + personalized greetings
"""

try:
    from gtts import gTTS
    import os
    print("✅ gTTS library found!")
except ImportError:
    print("❌ gTTS library not found. Installing...")
    import subprocess
    subprocess.check_call(["pip", "install", "gtts"])
    from gtts import gTTS
    import os
    print("✅ gTTS installed successfully!")

# Define output directory
output_dir = "frontend/public/audio"
os.makedirs(output_dir, exist_ok=True)

# Define ALL audio prompts
audio_files = {
    # Initial prompts (already exist)
    "welcome.mp3": {
        "text": "Welcome to Agrilogi Voice Booking Helpline.",
        "lang": "en",
        "tld": "co.in"
    },
    "tamil-prompt.mp3": {
        "text": "Ondru Tamil. Ondrai aluthavum.",
        "lang": "ta",
        "tld": "co.in"
    },
    "hindi-prompt.mp3": {
        "text": "Do Hindi ke liye. Do dabaiye.",
        "lang": "hi",
        "tld": "co.in"
    },
    "english-prompt.mp3": {
        "text": "For English, press three.",
        "lang": "en",
        "tld": "co.in"
    },
    
    # NEW: Personalized greetings (FEMALE VOICE!)
    "tamil-greeting.mp3": {
        "text": "Vanakkam. Ungalukku enna udhavi vendum endru sollungal. Endha pasal? Ethana kilo? Enga irundhu edukanum? Enga ship seiya vendum? Ungal muzhuvathum address sollungal.",
        "lang": "ta",
        "tld": "co.in"
    },
    "hindi-greeting.mp3": {
        "text": "Namaste. Kripya batayein. Kaunsi fasal hai? Kitna kilo hai? Kahan se lena hai? Kahan bhejni hai? Apna pura address batayein.",
        "lang": "hi",
        "tld": "co.in"
    },
    "english-greeting.mp3": {
        "text": "Welcome! Please tell me how I can help you. What crop or produce do you need to transport? How many kilograms is it? Where should we pick it up from, and where should we deliver it? Please provide your complete pickup and delivery addresses.",
        "lang": "en",
        "tld": "co.in"
    },
    
    # NEW: Confirmation templates
    "tamil-confirmation.mp3": {
        "text": "Nandri. Ungal booking confirm aayiduchu.",
        "lang": "ta",
        "tld": "co.in"
    },
    "hindi-confirmation.mp3": {
        "text": "Dhanyavaad. Aapka booking confirm ho gaya hai.",
        "lang": "hi",
        "tld": "co.in"
    },
    "english-confirmation.mp3": {
        "text": "Thank you. Your booking has been confirmed.",
        "lang": "en",
        "tld": "co.in"
    }
}

print("\n🎤 Generating ALL Audio Files for Agrilogi Voice Assistant\n")
print("=" * 70)

success_count = 0
total_size = 0

# Generate each audio file
for filename, config in audio_files.items():
    try:
        filepath = os.path.join(output_dir, filename)
        
        print(f"\n📝 Generating: {filename}")
        print(f"   Text: {config['text'][:60]}...")
        print(f"   Language: {config['lang']}")
        
        # Create TTS object with slow speed for clarity
        tts = gTTS(
            text=config['text'],
            lang=config['lang'],
            slow=True,  # Slower for better clarity
            tld=config['tld']
        )
        
        # Save to file
        tts.save(filepath)
        
        # Check file size
        file_size = os.path.getsize(filepath)
        total_size += file_size
        print(f"   ✅ Saved: {filepath} ({file_size:,} bytes)")
        success_count += 1
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

print("\n" + "=" * 70)
print(f"\n✅ Audio file generation complete! ({success_count}/{len(audio_files)} files)\n")

# List all generated files
print("📁 Generated Files:")
for filename in audio_files.keys():
    filepath = os.path.join(output_dir, filename)
    if os.path.exists(filepath):
        size_kb = os.path.getsize(filepath) / 1024
        print(f"   ✅ {filename:30s} ({size_kb:6.1f} KB)")
    else:
        print(f"   ❌ {filename:30s} (failed)")

print(f"\n📊 Total size: {total_size / 1024:.1f} KB")

print("\n" + "=" * 70)
print("\n🚀 Next Steps:")
print("   1. These audio files use FEMALE voice (gTTS default)")
print("   2. Update VoiceCallSimulator.tsx to use these files")
print("   3. Restart your Next.js dev server")
print("   4. Test the voice assistant")
print("\n   Result: 100% FEMALE voice throughout! 🎉\n")
