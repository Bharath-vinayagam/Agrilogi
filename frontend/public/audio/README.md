# 🎤 Audio Files for Agrilogi Voice Assistant

## Purpose
These audio files provide **perfect pronunciation** for the multilingual voice prompts, replacing browser text-to-speech with high-quality pre-recorded audio.

---

## Required Audio Files

Place these 4 audio files in this directory:

### 1. `welcome.mp3`
**Script (English):**
```
"Welcome to Agrilogi Voice Booking Helpline."
```
**Duration:** ~3 seconds  
**Language:** English (neutral Indian accent preferred)

---

### 2. `tamil-prompt.mp3`
**Script (Tamil):**
```
"Ondru Tamil. Ondrai azhuthavum."
(ஒன்று தமிழ். ஒன்றை அழுத்தவும்.)
```
**Translation:** "One for Tamil. Press one."  
**Duration:** ~3 seconds  
**Language:** Tamil (native speaker required)

---

### 3. `hindi-prompt.mp3`
**Script (Hindi):**
```
"Do Hindi ke liye. Do dabaiye."
(दो हिंदी के लिए. दो दबाइए.)
```
**Translation:** "Two for Hindi. Press two."  
**Duration:** ~3 seconds  
**Language:** Hindi (native speaker required)

---

### 4. `english-prompt.mp3`
**Script (English):**
```
"For English, press three."
```
**Duration:** ~2 seconds  
**Language:** English

---

## How to Record (3 Easy Methods)

### Method 1: Using Your Smartphone (Easiest)
1. **Open Voice Recorder app** on your phone
2. **Record each script** clearly and slowly
3. **Save recordings** with appropriate names
4. **Transfer to computer** via USB or email
5. **Convert to MP3** (if needed) using https://cloudconvert.com
6. **Place files** in this `frontend/public/audio/` folder

### Method 2: Using Online TTS (Quick but less natural)
1. Visit: https://ttsfree.com or https://ttsmp3.com
2. Select language: Tamil/Hindi/English
3. Paste script text
4. Download MP3
5. Rename and place in this folder

### Method 3: Professional (Best Quality)
1. Hire voice artists on Fiverr (₹500-1000 total)
2. Provide scripts above
3. Request: MP3 format, 32kbps mono, neutral tone
4. Download and place in this folder

---

## Audio Specifications

### Recommended Settings:
- **Format:** MP3
- **Bitrate:** 32kbps (small file size, good quality for voice)
- **Channels:** Mono (voice only)
- **Sample Rate:** 22050 Hz or 44100 Hz
- **Volume:** Normalize to -6dB (clear but not distorted)

### File Size:
- Each file should be ~30-50 KB
- Total: ~150 KB for all 4 files

---

## Fallback Behavior

If audio files are **not present**, the system automatically falls back to:
- ✅ Browser text-to-speech (current behavior)
- ✅ Slower speech rate for clarity
- ✅ Language-specific voice selection
- ⚠️ May have pronunciation issues with Tamil/Hindi

**With audio files present:**
- ✅ Perfect native pronunciation
- ✅ Natural voice quality
- ✅ Consistent across all browsers
- ✅ Professional user experience

---

## Testing After Adding Files

1. **Place files in this directory**
2. **Restart development server:** `npm run dev`
3. **Open farmer dashboard**
4. **Click "START REAL VOICE CALL"**
5. **Listen for your recorded audio**

**Check browser console for:**
```
Using audio file: /audio/welcome.mp3
Using audio file: /audio/tamil-prompt.mp3
Using audio file: /audio/hindi-prompt.mp3
Using audio file: /audio/english-prompt.mp3
```

**If you see TTS fallback messages:**
```
Audio file not found: tamil-prompt.mp3, using TTS fallback
```
→ File is missing or incorrectly named

---

## Quick Recording Script (Tamil Speaker)

### Tamil Speaker:
```
"Ondru Tamil. Ondrai azhuthavum."
```
**Pronunciation Guide:**
- Ondru = Own-dru (ஒன்று)
- Tamil = Tah-mil (தமிழ்)
- Ondrai = Own-drai (ஒன்றை)
- Azhuthavum = Ah-zhu-tha-vum (அழுத்தவும்)

### Hindi Speaker:
```
"Do Hindi ke liye. Do dabaiye."
```
**Pronunciation Guide:**
- Do = Doh (दो)
- Hindi = Hin-dee (हिंदी)
- Ke liye = Kay lee-yay (के लिए)
- Dabaiye = Duh-bye-yay (दबाइए)

---

## Voice Talent Recommendations

### Professional Services:
1. **Fiverr:** Search "Tamil voice over" or "Hindi voice over"
   - Cost: ₹300-500 per file
   - Turnaround: 24 hours
   
2. **Upwork:** Hire Indian voice artists
   - Cost: ₹500-1000 for all 4 files
   - Quality: Professional studio recording

3. **Local Recording:**
   - Ask Tamil/Hindi speaking colleagues
   - Use quiet room
   - Smartphone recorder is sufficient

---

## Sample Online TTS Services

### For Tamil:
- https://ttsfree.com (Select "Tamil India")
- https://www.naturalreaders.com (Tamil voice)
- Google Cloud TTS (Best quality, requires API key)

### For Hindi:
- https://ttsfree.com (Select "Hindi India")  
- https://ttsmp3.com (Multiple Hindi voices)
- Azure Speech (Best quality, requires API key)

---

## File Checklist

Before deploying to production:

- [ ] `welcome.mp3` recorded and placed
- [ ] `tamil-prompt.mp3` recorded by Tamil native speaker
- [ ] `hindi-prompt.mp3` recorded by Hindi native speaker
- [ ] `english-prompt.mp3` recorded
- [ ] All files tested in browser
- [ ] Volume levels normalized
- [ ] File sizes optimized (< 50KB each)
- [ ] Pronunciation verified by native speakers

---

## Current Status

**Files Present:** 0 / 4  
**TTS Fallback:** Active ✅  
**Action Needed:** Record and add audio files

---

## Need Help?

### Quick Test:
1. Download sample MP3 from: https://ttsmp3.com
2. Rename to `tamil-prompt.mp3`
3. Place in this folder
4. Test if system picks it up

### Questions:
- Check `VOICE_QUALITY_IMPROVEMENT_GUIDE.md` in project root
- Consult `HOW_TO_USE_VOICE_ASSISTANT.md` for usage guide

---

**Remember:** Even one audio file is better than none!  
Start with the most important (Tamil) and add others later.

**Priority Order:**
1. `tamil-prompt.mp3` (most critical - Tamil farmers)
2. `hindi-prompt.mp3` (important - Hindi farmers)
3. `welcome.mp3` (nice to have - everyone hears it)
4. `english-prompt.mp3` (least critical - English is clear in TTS)
