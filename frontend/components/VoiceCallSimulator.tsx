"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle, Mic, Phone, PhoneOff, RefreshCw, ShieldAlert, Volume2 } from "lucide-react";
import { api } from "@/services/api";

type CallState =
  | "IDLE"
  | "DATE_SLOT_SELECT"
  | "LANGUAGE_SELECTION"
  | "RECORDING"
  | "UPLOADING"
  | "AI_PROCESSING"
  | "BOOKING_CREATED";

type Language = "Tamil" | "Hindi" | "English";

interface VoiceCallSimulatorProps {
  onBookingCreated?: () => void;
  onNewNotification?: (notification: {
    id: string;
    crop: string;
    weightKg: number;
    village: string;
    timestamp: string;
  }) => void;
  farmerName?: string;
}

const demoTranscripts: Record<Language, string> = {
  Tamil: "En pasal thakkali. Naanu 400 kilo irukku. En address 12/4 Gandhi Street, Melma village, Kanchipuram district, Tamil Nadu. Koyambedu Mandi ku anupanum.",
  Hindi: "Meri fasal baingan hai. Mere paas 200 kilo hai. Mera address 25/8 Main Road, Sevoor gaon, Kanchipuram district, Tamil Nadu hai. Koyambedu Mandi bhejni hai.",
  English: "My crop is tomatoes. I have 350 kilograms. My address is 18/2 Market Street, Athur village, Kanchipuram district, Tamil Nadu. Please ship to Koyambedu Mandi."
};

export function VoiceCallSimulator({ onBookingCreated, onNewNotification, farmerName = "Farmer" }: VoiceCallSimulatorProps) {
  const [callState, setCallState] = useState<CallState>("IDLE");
  const [selectedLanguage, setSelectedLanguage] = useState<Language>("English");
  const [statusText, setStatusText] = useState("Call is offline");
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [transcript, setTranscript] = useState("");
  const [extractedData, setExtractedData] = useState<any>(null);
  const [confidence, setConfidence] = useState<any>(null);
  const [bookingDetails, setBookingDetails] = useState<any>(null);
  const [speechAvailable, setSpeechAvailable] = useState(false);
  const [voiceList, setVoiceList] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedDate, setSelectedDate] = useState("");
  const [selectedSlot, setSelectedSlot] = useState<"morning" | "afternoon" | "evening" | "">("");
  const [isTimeFlexible, setIsTimeFlexible] = useState(true);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const recognitionRef = useRef<any>(null);
  const liveTranscriptRef = useRef("");
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const isPlayingAudioRef = useRef(false);
  const isSpeakingRef = useRef(false);

  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      const speech = window.speechSynthesis;
      synthRef.current = speech;

      const loadVoices = () => {
        const voices = speech.getVoices();
        if (voices.length > 0) {
          setVoiceList(voices);
          setSpeechAvailable(true);
        }
      };

      loadVoices();
      speech.onvoiceschanged = loadVoices;
    }

    return () => {
      stopRecordingTimer();
      stopSpeechRecognition();
      stopAllAudio(); // Stop all audio on unmount
      if (synthRef.current) {
        synthRef.current.onvoiceschanged = null;
      }
    };
  }, []);

  function startRecordingTimer() {
    stopRecordingTimer();
    setRecordingSeconds(0);
    timerRef.current = setInterval(() => setRecordingSeconds((prev) => prev + 1), 1000);
  }

  function stopRecordingTimer() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  function formatTime(secs: number) {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  }

  function stopAllAudio() {
    // Stop all TTS
    if (synthRef.current) {
      synthRef.current.cancel();
      isSpeakingRef.current = false;
    }
    
    // Stop all audio players
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
      audioPlayerRef.current = null;
      isPlayingAudioRef.current = false;
    }
    
    console.log("🛑 All audio stopped");
  }

  function getLanguageCode(language: Language): string {
    switch (language) {
      case "Tamil": return "ta-IN";
      case "Hindi": return "hi-IN";
      default: return "en-IN";
    }
  }

  function getLanguagePrompt(language: Language, name: string) {
    switch (language) {
      case "Tamil":
        // Optimized phonetics for better TTS pronunciation
        return `Vanakkam ${name}. Ungalukku enna udhavi vendum endru sollungal. Endha pasal? Ethana kilo? Enga irundhu edukanum? Enga ship seiya vendum? Ungal muzhuvathum address sollungal.`;

      case "Hindi":
        // Optimized phonetics for better TTS pronunciation
        return `Namaste ${name}. Kripya batayein. Kaunsi fasal hai? Kitna kilo hai? Kahan se lena hai? Kahan bhejni hai? Apna pura address batayein.`;

      default:
        return `Welcome ${name}! Please tell me how I can help you. What crop or produce do you need to transport? How many kilograms is it? Where should we pick it up from, and where should we deliver it? Please provide your complete pickup and delivery addresses.`;
    }
  }

  function getConfirmationText(language: Language, weight: number, crop: string, village: string, bId: string) {
    switch (language) {
      case "Tamil":
        // Simplified for better pronunciation
        return `Nandri. ${weight} kilo ${crop}, ${village} irundhu. Ungal booking number ${bId}.`;
      case "Hindi":
        // Simplified for better pronunciation
        return `Dhanyavaad. ${weight} kilo ${crop}, ${village} se. Aapka booking number ${bId}.`;
      default:
        return `Thank you. We recorded ${weight} kilograms of ${crop} from ${village}. Your booking ID is ${bId}.`;
    }
  }

  function getSpeechVoice(langCode: string) {
    const voices = voiceList.length > 0 ? voiceList : synthRef.current?.getVoices() ?? [];
    if (voices.length === 0) {
      console.warn("⚠️ No voices available");
      return null;
    }
    
    const requestedPrefix = langCode.slice(0, 2).toLowerCase();
    
    // PRIORITY 1: Female voice with exact language match
    let femaleVoice = voices.find((voice) => {
      const voiceLang = voice.lang.toLowerCase();
      const voiceName = voice.name.toLowerCase();
      const isFemale = voiceName.includes('female') || voiceName.includes('woman') || 
                      voiceName.includes('heera') || voiceName.includes('lekha') ||
                      voiceName.includes('kalpana') || voiceName.includes('swara') ||
                      voiceName.includes('aditi') || voiceName.includes('raveena') ||
                      voiceName.includes('samantha') || voiceName.includes('victoria');
      
      return voiceLang.startsWith(requestedPrefix) && isFemale;
    });
    
    if (femaleVoice) {
      console.log(`✅ Selected FEMALE voice: ${femaleVoice.name} (${femaleVoice.lang})`);
      return femaleVoice;
    }
    
    // PRIORITY 2: Any voice with language match (fallback)
    const langMatch = voices.find((voice) => voice.lang.toLowerCase().startsWith(requestedPrefix));
    if (langMatch) {
      console.warn(`⚠️ Using non-female voice: ${langMatch.name} (${langMatch.lang})`);
      return langMatch;
    }
    
    // PRIORITY 3: English female fallback
    const englishFemale = voices.find((voice) => {
      const voiceName = voice.name.toLowerCase();
      return voice.lang.toLowerCase().startsWith("en") && 
             (voiceName.includes('female') || voiceName.includes('samantha') || voiceName.includes('victoria'));
    });
    if (englishFemale) {
      console.warn(`⚠️ Using English female fallback: ${englishFemale.name}`);
      return englishFemale;
    }
    
    // Final fallback
    console.warn(`⚠️ Using default voice: ${voices[0]?.name || 'system default'}`);
    return voices[0] || null;
  }

  function speak(text: string, langCode = "en-IN", onEnd?: () => void, rate = 0.80) {
    // Stop any existing speech first
    stopAllAudio();
    
    if (!synthRef.current) {
      console.error("❌ Speech synthesis not available");
      onEnd?.();
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    const voice = getSpeechVoice(langCode);
    
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    } else {
      utterance.lang = langCode;
    }
    
    // Optimized speech parameters
    utterance.rate = rate;
    utterance.volume = 1.0;
    utterance.pitch = langCode.startsWith('ta') ? 1.1 : langCode.startsWith('hi') ? 1.05 : 1.0;
    
    utterance.onstart = () => {
      isSpeakingRef.current = true;
      console.log(`🔊 TTS Started: "${text.substring(0, 50)}..."`);
    };
    
    utterance.onend = () => {
      isSpeakingRef.current = false;
      console.log("✅ TTS Completed");
      onEnd?.();
    };
    
    utterance.onerror = (error) => {
      isSpeakingRef.current = false;
      console.error("❌ TTS Error:", error);
      onEnd?.();
    };
    
    synthRef.current.speak(utterance);
  }


  function playAudio(filename: string, onEnd?: () => void) {
    // Stop ALL audio before playing new one
    stopAllAudio();
    
    const audio = new Audio(`/audio/${filename}`);
    audioPlayerRef.current = audio;
    isPlayingAudioRef.current = true;
    
    audio.onloadeddata = () => {
      console.log(`🎵 Audio loaded: ${filename}`);
    };
    
    audio.onplay = () => {
      console.log(`▶️ Playing audio: ${filename}`);
    };
    
    audio.onended = () => {
      console.log(`✅ Audio finished: ${filename}`);
      audioPlayerRef.current = null;
      isPlayingAudioRef.current = false;
      onEnd?.();
    };
    
    audio.onerror = () => {
      console.log(`❌ Audio file not found: ${filename}, using TTS fallback`);
      audioPlayerRef.current = null;
      isPlayingAudioRef.current = false;
      useTTSFallback(filename, onEnd);
    };
    
    audio.play().catch((err) => {
      console.log(`❌ Audio playback failed for: ${filename}`, err);
      audioPlayerRef.current = null;
      isPlayingAudioRef.current = false;
      useTTSFallback(filename, onEnd);
    });
  }

  function useTTSFallback(filename: string, onEnd?: () => void) {
    // Map audio files to TTS text with optimized settings
    if (filename === 'welcome.mp3') {
      speak("Welcome to Agrilogi Voice Booking Helpline.", "en-IN", onEnd, 0.85);
    } else if (filename === 'tamil-prompt.mp3') {
      speak("Ondru Tamil. Ondrai aluthavum.", "ta-IN", onEnd, 0.70);
    } else if (filename === 'hindi-prompt.mp3') {
      speak("Do Hindi ke liye. Do dabaiye.", "hi-IN", onEnd, 0.75);
    } else if (filename === 'english-prompt.mp3') {
      speak("For English, press three.", "en-IN", onEnd, 0.85);
    } else if (filename === 'tamil-greeting.mp3') {
      speak("Vanakkam. Ungalukku enna udhavi vendum endru sollungal. Endha pasal? Ethana kilo? Enga irundhu edukanum? Enga ship seiya vendum? Ungal muzhuvathum address sollungal.", "ta-IN", onEnd, 0.65);
    } else if (filename === 'hindi-greeting.mp3') {
      speak("Namaste. Kripya batayein. Kaunsi fasal hai? Kitna kilo hai? Kahan se lena hai? Kahan bhejni hai? Apna pura address batayein.", "hi-IN", onEnd, 0.70);
    } else if (filename === 'english-greeting.mp3') {
      speak("Welcome! Please tell me how I can help you. What crop or produce do you need to transport? How many kilograms is it? Where should we pick it up from, and where should we deliver it?", "en-IN", onEnd, 0.75);
    } else if (filename === 'tamil-confirmation.mp3') {
      speak("Nandri. Ungal booking confirm aayiduchu.", "ta-IN", onEnd, 0.70);
    } else if (filename === 'hindi-confirmation.mp3') {
      speak("Dhanyavaad. Aapka booking confirm ho gaya hai.", "hi-IN", onEnd, 0.75);
    } else if (filename === 'english-confirmation.mp3') {
      speak("Thank you. Your booking has been confirmed.", "en-IN", onEnd, 0.80);
    } else {
      onEnd?.();
    }
  }

  function clearPreviousCallData() {
    liveTranscriptRef.current = "";
    setTranscript("");
    setExtractedData(null);
    setConfidence(null);
    setBookingDetails(null);
    setSelectedDate("");
    setSelectedSlot("");
    setIsTimeFlexible(true);
  }

  function startCall() {
    stopAllAudio(); // Stop everything before starting
    clearPreviousCallData();
    // Go directly to date/slot selection FIRST
    setCallState("DATE_SLOT_SELECT");
    setStatusText("Select pickup date and time slot");
  }

  function proceedToLanguageSelection() {
    if (!selectedDate || !selectedSlot) {
      alert("Please select both pickup date and time slot");
      return;
    }
    
    setCallState("LANGUAGE_SELECTION");
    setStatusText("Connecting to voice assistant...");
    
    // Speak multilingual instructions sequentially
    speakMultilingualWelcome();
  }

  function speakMultilingualWelcome() {
    // Try to use pre-recorded audio files first, fallback to TTS
    playAudio('welcome.mp3', () => {
      playAudio('tamil-prompt.mp3', () => {
        playAudio('hindi-prompt.mp3', () => {
          playAudio('english-prompt.mp3');
        });
      });
    });
  }

  function handleKeyPress(num: number) {
    if (callState !== "LANGUAGE_SELECTION") return;
    
    // CRITICAL: Stop all audio immediately when user presses button
    stopAllAudio();
    
    const lang = num === 1 ? "Tamil" : num === 2 ? "Hindi" : num === 3 ? "English" : null;
    if (lang) selectLanguage(lang);
  }

  function selectLanguage(lang: Language) {
    // Ensure all audio is stopped
    stopAllAudio();
    
    setSelectedLanguage(lang);
    setStatusText(`Listening in ${lang}... Speak now`);
    setCallState("RECORDING");
    
    // Start recording and speech recognition immediately
    startRecording(lang);

    // Play greeting prompt
    const audioFile = lang === "Tamil" ? "tamil-greeting.mp3" : 
                      lang === "Hindi" ? "hindi-greeting.mp3" : 
                      "english-greeting.mp3";
    
    console.log(`🎵 Playing personalized greeting: ${audioFile}`);
    playAudio(audioFile);
  }

  async function startRecording(language: Language) {
    liveTranscriptRef.current = "";
    setTranscript("");
    setCallState("RECORDING");
    setStatusText("Listening... (Speak your crop, weight, and village)");
    startRecordingTimer();
    startSpeechRecognition(language);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      mediaRecorder.onstop = () => {
        stopSpeechRecognition();
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        uploadAudio(audioBlob);
      };
      mediaRecorder.start();
    } catch {
      setStatusText("Listening with browser speech fallback...");
    }
  }

  function startSpeechRecognition(language: Language) {
    if (typeof window === "undefined") return;
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language === "Tamil" ? "ta-IN" : language === "Hindi" ? "hi-IN" : "en-IN";
    recognition.onresult = (event: any) => {
      let interimText = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const chunk = event.results[index][0]?.transcript ?? "";
        if (event.results[index].isFinal) {
          liveTranscriptRef.current = `${liveTranscriptRef.current} ${chunk}`.trim();
        } else {
          interimText += `${chunk} `;
        }
      }
      const visibleTranscript = `${liveTranscriptRef.current} ${interimText}`.trim();
      if (visibleTranscript) setTranscript(visibleTranscript);
    };
    recognition.onerror = () => undefined;
    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      recognitionRef.current = null;
    }
  }

  function stopSpeechRecognition() {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch {
      // It may already be stopped by the browser.
    }
    recognitionRef.current = null;
  }

  function endCall() {
    stopRecordingTimer();
    stopSpeechRecognition();
    stopAllAudio(); // Stop all audio when ending call
    
    if (callState === "RECORDING") {
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
      } else {
        uploadTranscriptOnly();
      }
      return;
    }
    
    setCallState("IDLE");
    setStatusText("Call ended");
  }

  async function uploadAudio(audioBlob: Blob) {
    const formData = new FormData();
    formData.append("audio_file", audioBlob, "call_recording.webm");
    formData.append("language", selectedLanguage);
    formData.append("farmer_name", farmerName); // Send logged-in farmer name
    appendBestTranscript(formData);
    await processUpload(formData, selectedLanguage);
  }

  async function uploadTranscriptOnly() {
    const formData = new FormData();
    formData.append("language", selectedLanguage);
    formData.append("farmer_name", farmerName); // Send logged-in farmer name
    appendBestTranscript(formData);
    await processUpload(formData, selectedLanguage);
  }

  function appendBestTranscript(formData: FormData) {
    const bestTranscript = (liveTranscriptRef.current || transcript).trim();
    if (bestTranscript) {
      formData.append("transcript_text", bestTranscript);
    }
  }

  async function processUpload(formData: FormData, language: Language) {
    const bestTranscript = (liveTranscriptRef.current || transcript).trim();
    if (!bestTranscript && (!audioChunksRef.current || audioChunksRef.current.length === 0)) {
      setCallState("IDLE");
      setStatusText("⚠️ No speech detected. Please speak clearly into your microphone.");
      return;
    }

    setCallState("AI_PROCESSING");
    setStatusText("Processing speech with AI...");
    try {
      const res = await api.uploadVoice(formData);
      if (!res || !res.extracted) {
        setCallState("IDLE");
        setStatusText("⚠️ Could not recognize speech. Please try speaking again.");
        return;
      }
      handleCallSuccess(res, language);
    } catch (err: any) {
      setCallState("IDLE");
      setStatusText(err?.message || "⚠️ No speech detected. Please speak into your microphone and try again.");
    }
  }

  function handleCallSuccess(res: any, language: Language) {
    setTranscript(res.transcript);
    setExtractedData(res.extracted);
    setConfidence(res.confidence);
    
    // Go directly to AI processing, then create booking
    setCallState("AI_PROCESSING");
    setStatusText("Creating booking...");

    // Stop all audio
    stopAllAudio();
    
    // Create booking immediately with date/slot already selected
    createBookingWithExtractedData(res, language);
  }

  async function createBookingWithExtractedData(res: any, language: Language) {
    // Only use extracted name if not "Unknown Farmer" and not default Suresh
    const resolvedFarmer = (res.extracted?.farmer_name && res.extracted.farmer_name !== "Unknown Farmer" && res.extracted.farmer_name !== "Suresh")
      ? res.extracted.farmer_name
      : farmerName;

    const resolvedWeight = Number(res.extracted?.weight) || 0;
    if (resolvedWeight <= 0) {
      setCallState("IDLE");
      setStatusText("⚠️ Could not detect crop weight. Please speak weight (e.g. 250 kg).");
      return;
    }

    const payload = {
      farmer_name: resolvedFarmer,
      phone: res.extracted?.phone || "+91 90000 00000",
      village: res.extracted?.source_village || res.extracted?.village || "Unknown Village",
      crop: res.extracted?.crop || "Unknown Crop",
      weight_kg: resolvedWeight,
      destination: res.extracted?.destination_village || "Koyambedu Mandi",
      pickup_date: selectedDate,
      pickup_slot: selectedSlot,
      is_time_flexible: isTimeFlexible,
      source: "Voice Call",
      language: language === "Tamil" ? "ta" : language === "Hindi" ? "hi" : "en",
      confidence: res.confidence,
      review_required: res.confidence?.farmer_name < 70 || res.confidence?.village < 70 || res.confidence?.crop < 70 || res.confidence?.weight < 70
    };

    try {
      const booking = await api.createBooking(payload);
      setBookingDetails(booking);
      setCallState("BOOKING_CREATED");
      setStatusText("Booking created");

      // Play confirmation audio
      const audioFile = language === "Tamil" ? "tamil-confirmation.mp3" : 
                        language === "Hindi" ? "hindi-confirmation.mp3" : 
                        "english-confirmation.mp3";
      
      console.log(`🎵 Playing confirmation: ${audioFile}`);
      playAudio(audioFile);

      onBookingCreated?.();
      if (onNewNotification && booking) {
        onNewNotification({
          id: booking.id,
          crop: booking.crop,
          weightKg: booking.weightKg,
          village: booking.village,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        });
      }
    } catch (err) {
      console.error("Error creating booking:", err);
      setCallState("IDLE");
      setStatusText("Booking failed. Please try again.");
    }
  }

  async function startDemoCall(lang: Language) {
    synthRef.current?.cancel();
    clearPreviousCallData();
    setSelectedLanguage(lang);
    
    // For demo, auto-set date and slot to skip that step
    setSelectedDate(new Date().toISOString().split('T')[0]);
    setSelectedSlot("morning");
    setIsTimeFlexible(true);
    
    setCallState("RECORDING");
    setStatusText(`Demo call started: ${lang}`);
    setTranscript(demoTranscripts[lang]);
    liveTranscriptRef.current = demoTranscripts[lang];
    startRecordingTimer();

    window.setTimeout(async () => {
      stopRecordingTimer();
      
      // Simulate extraction result
      const demoExtraction = {
        transcript: demoTranscripts[lang],
        extracted: lang === "Tamil" 
          ? { farmer_name: "Arumugam", village: "Melma", crop: "Tomato", weight: 400 }
          : lang === "Hindi"
          ? { farmer_name: "Ramesh", village: "Sevoor", crop: "Eggplant", weight: 200 }
          : { farmer_name: "Suresh", village: "Athur", crop: "Tomato", weight: 350 },
        confidence: lang === "Tamil"
          ? { farmer_name: 94, village: 92, crop: 96, weight: 97 }
          : lang === "Hindi"
          ? { farmer_name: 65, village: 88, crop: 90, weight: 58 }
          : { farmer_name: 92, village: 90, crop: 95, weight: 93 }
      };
      
      handleCallSuccess(demoExtraction, lang);
    }, 1200);
  }

  return (
    <div className="space-y-4">
      <section className="relative flex min-h-[460px] flex-col justify-between overflow-hidden rounded-xl border border-stone-200 bg-white p-5 shadow-panel">
        <div className="relative z-10 flex w-full flex-col items-center text-center">
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-soil/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-soil">
            Agrilogi Voice Assistant
          </div>
          <h2 className="text-xl font-extrabold text-soil">Book crop transport using voice</h2>
          <p className="mt-1 max-w-xs text-xs text-stone-500">
            ✨ Click "Start Call" → Choose Language → Speak Your Details
          </p>

          <div className="mt-6 flex min-h-[140px] w-full max-w-xs flex-col items-center justify-center rounded-xl bg-stone-900 p-5 text-stone-100 shadow-inner">
            {callState === "IDLE" && (
              <div className="space-y-1">
                <p className="text-2xl font-black tracking-widest text-white">Ready to Call</p>
                <p className="text-xs text-stone-500">Press start call to begin</p>
              </div>
            )}

            {callState === "LANGUAGE_SELECTION" && (
              <div className="space-y-3">
                <p className="animate-pulse text-xs font-bold text-river">CHOOSE LANGUAGE / மொழியை தேர்ந்தெடுக்கவும் / भाषा चुनें</p>
                <div className="space-y-1 text-left text-xs text-stone-300">
                  <p>Press <span className="font-bold text-white">1</span> - Tamil / தமிழ்</p>
                  <p>Press <span className="font-bold text-white">2</span> - Hindi / हिंदी</p>
                  <p>Press <span className="font-bold text-white">3</span> - English</p>
                </div>
              </div>
            )}

            {(callState === "RECORDING" || callState === "UPLOADING" || callState === "AI_PROCESSING") && (
              <div className="w-full space-y-2">
                <div className="flex items-center justify-center gap-2">
                  <div className="h-2.5 w-2.5 animate-ping rounded-full bg-red-600" />
                  <p className="text-xs font-bold uppercase tracking-wider text-stone-400">{statusText}</p>
                </div>
                <p className="text-3xl font-black tracking-wide text-white">{formatTime(recordingSeconds)}</p>
                <p className="text-[11px] font-bold text-harvest">{selectedLanguage} helpline mode</p>
                <div className="mt-2 rounded-lg bg-stone-800/80 p-2 text-left border border-stone-700">
                  <p className="text-[9px] uppercase font-bold text-stone-400">🎙️ Spoken Words Heard:</p>
                  <p className="mt-0.5 text-xs text-emerald-400 font-mono italic break-words">
                    {transcript || "Listening for speech... (speak your crop, weight & village)"}
                  </p>
                </div>
              </div>
            )}

            {callState === "BOOKING_CREATED" && (
              <div className="space-y-1 text-center">
                <CheckCircle className="mx-auto text-field" size={30} />
                <p className="mt-2 text-xs font-bold uppercase tracking-wider text-field">Booking Created</p>
                <p className="text-lg font-black text-white">{bookingDetails?.id || "KB1024"}</p>
                <p className="text-[10px] text-stone-400">SMS confirmation sent</p>
              </div>
            )}

            {callState === "DATE_SLOT_SELECT" && (
              <div className="space-y-1 text-center">
                <p className="text-xs font-bold uppercase tracking-wider text-harvest">Select Pickup Details</p>
                <p className="text-[10px] text-stone-400 mt-1">Choose date and time slot below</p>
              </div>
            )}

          </div>

          <div className="mt-6 grid w-full max-w-xs grid-cols-3 gap-3">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, "*", 0, "#"].map((key) => {
              const isSelectable = callState === "LANGUAGE_SELECTION" && typeof key === "number" && key >= 1 && key <= 3;
              return (
                <button
                  className={`focus-ring grid h-12 place-items-center rounded-lg border text-sm font-bold transition-all ${
                    isSelectable
                      ? "border-soil bg-soil/5 text-soil hover:bg-soil hover:text-white"
                      : "cursor-not-allowed border-stone-200 bg-stone-50 text-stone-400"
                  }`}
                  disabled={callState !== "LANGUAGE_SELECTION"}
                  key={key}
                  onClick={() => typeof key === "number" && handleKeyPress(key)}
                  type="button"
                >
                  {key}
                </button>
              );
            })}
          </div>

          {/* Date and Slot Selection Form */}
          {callState === "DATE_SLOT_SELECT" && (
            <div className="mt-6 w-full max-w-xs space-y-3 rounded-lg border-2 border-harvest/30 bg-harvest/5 p-4">
              <h3 className="text-sm font-bold text-soil text-center">📅 Select Pickup Date & Time</h3>
              
              <div>
                <label className="text-xs font-semibold text-stone-700 block mb-1.5">Pickup Date</label>
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                  className="focus-ring w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                  required
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-stone-700 block mb-1.5">Pickup Time Slot</label>
                <select
                  value={selectedSlot}
                  onChange={(e) => setSelectedSlot(e.target.value as "morning" | "afternoon" | "evening")}
                  className="focus-ring w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                  required
                >
                  <option value="">Select time slot</option>
                  <option value="morning">🌅 Morning (6:00 AM - 10:00 AM)</option>
                  <option value="afternoon">☀️ Afternoon (11:00 AM - 3:00 PM)</option>
                  <option value="evening">🌆 Evening (4:00 PM - 8:00 PM)</option>
                </select>
              </div>

              <div className="flex items-center gap-2 rounded-lg border border-stone-200 bg-white p-2.5">
                <input
                  type="checkbox"
                  id="voice_flexible"
                  checked={isTimeFlexible}
                  onChange={(e) => setIsTimeFlexible(e.target.checked)}
                  className="h-4 w-4 rounded border-stone-300 text-field focus:ring-field"
                />
                <label htmlFor="voice_flexible" className="text-xs text-stone-700 cursor-pointer flex-1">
                  <span className="font-semibold">I'm flexible with timing</span>
                  <span className="text-stone-500 block text-[10px]">Better rates when system optimizes pickup</span>
                </label>
              </div>

              <button
                onClick={proceedToLanguageSelection}
                disabled={!selectedDate || !selectedSlot}
                className="focus-ring w-full inline-flex items-center justify-center gap-2 rounded-lg bg-field px-4 py-3 text-sm font-bold text-white disabled:bg-stone-300 disabled:cursor-not-allowed hover:bg-field/90 transition-all"
              >
                <Phone size={18} />
                Continue to Voice Call
              </button>
            </div>
          )}
        </div>

        <div className="relative z-10 mx-auto mt-6 flex w-full max-w-xs flex-col gap-2">
          {callState === "IDLE" || callState === "BOOKING_CREATED" ? (
            <>
              <button className="focus-ring inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-field py-4 text-base font-black text-white shadow-lg hover:bg-field/90 transition-all" onClick={startCall} type="button">
                <Phone size={20} />
                START REAL VOICE CALL
              </button>
              <p className="text-center text-[10px] text-stone-500 italic">
                Real voice assistant with language selection
              </p>
            </>
          ) : callState === "DATE_SLOT_SELECT" ? (
            <button className="focus-ring inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-stone-400 py-3 text-sm font-bold text-white shadow-md" onClick={endCall} type="button">
              <PhoneOff size={18} />
              Cancel Booking
            </button>
          ) : (
            <button className="focus-ring inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-chilli py-3 text-sm font-bold text-white shadow-md" onClick={endCall} type="button">
              <PhoneOff size={18} />
              End Call
            </button>
          )}
        </div>
      </section>

      <div className="space-y-4">
        {(transcript || extractedData) && (
          <section className="space-y-4 rounded-xl border border-stone-200 bg-white p-5 shadow-panel">
            <div>
              <h3 className="flex items-center gap-1.5 text-sm font-bold uppercase tracking-wider text-soil">
                <RefreshCw className="text-river" size={15} />
                Live Helpline Analysis
              </h3>
              <p className="text-[11px] text-stone-500">Transcript text, extracted entities, and confidence scores.</p>
            </div>

            {transcript && (
              <div className="rounded-lg border border-stone-100 bg-stone-50 p-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Transcript</p>
                <p className="mt-1.5 text-xs font-medium italic leading-relaxed text-stone-700">"{transcript}"</p>
              </div>
            )}

            {extractedData && (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Extracted Entities</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {[
                    ["Farmer Name", "farmer_name", extractedData.farmer_name],
                    ["From (Pickup)", "source_village", extractedData.source_village || extractedData.village],
                    ["To (Delivery)", "destination_village", extractedData.destination_village || "Koyambedu Mandi"],
                    ["Crop Type", "crop", extractedData.crop],
                    ["Weight", "weight", extractedData.weight ? `${extractedData.weight} kg` : ""]
                  ].map(([label, key, value]) => (
                    <div className="flex flex-col rounded-lg border border-stone-100 bg-white p-2" key={key}>
                      <span className="text-[9px] font-bold uppercase text-stone-400">{label}</span>
                      <span className="mt-0.5 text-xs font-bold text-soil">{value || "-"}</span>
                      {confidence && confidence[key as string] !== undefined && (
                        <span className={`mt-1 text-[9px] font-bold ${confidence[key as string] >= 70 ? "text-field" : "text-chilli"}`}>
                          Confidence: {confidence[key as string]}%
                        </span>
                      )}
                    </div>
                  ))}
                </div>

                {bookingDetails?.reviewRequired && (
                  <div className="mt-2 flex items-start gap-2 rounded-lg border border-chilli/20 bg-chilli/10 p-2.5 text-chilli">
                    <ShieldAlert className="mt-0.5 flex-shrink-0" size={16} />
                    <div>
                      <p className="text-[10px] font-black uppercase tracking-wider">Manual Review Required</p>
                      <p className="mt-0.5 text-[10px] leading-tight">One or more confidence scores are below 70%.</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
