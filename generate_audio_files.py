"""
Generate Audio Files for Agrilogi Voice Assistant
Using Google Text-to-Speech (gTTS) - Free and Good Quality
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

# Create directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Define audio prompts
audio_files = {
    "welcome.mp3": {
        "text": "Welcome to Agrilogi Voice Booking Helpline.",
        "lang": "en",
        "tld": "co.in"  # Indian English accent
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
    }
}

print("\n🎤 Generating Audio Files for Agrilogi Voice Assistant\n")
print("=" * 60)

# Generate each audio file
for filename, config in audio_files.items():
    try:
        filepath = os.path.join(output_dir, filename)
        
        print(f"\n📝 Generating: {filename}")
        print(f"   Text: {config['text']}")
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
        print(f"   ✅ Saved: {filepath} ({file_size} bytes)")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("\n✅ Audio file generation complete!\n")

# List all generated files
print("📁 Generated Files:")
for filename in audio_files.keys():
    filepath = os.path.join(output_dir, filename)
    if os.path.exists(filepath):
        size_kb = os.path.getsize(filepath) / 1024
        print(f"   ✅ {filename} ({size_kb:.1f} KB)")
    else:
        print(f"   ❌ {filename} (failed)")

print("\n🚀 Next Steps:")
print("   1. Restart your Next.js dev server (Ctrl+C, then npm run dev)")
print("   2. Open farmer dashboard")
print("   3. Click 'START REAL VOICE CALL'")
print("   4. Enjoy perfect pronunciation!")
print("\n   No more 404 errors! 🎉\n")
