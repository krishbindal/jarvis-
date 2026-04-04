from vosk import Model, KaldiRecognizer
import sounddevice as sd
import json

# 🔥 CONFIG

MODEL_PATH = "voice/model"

# 🔥 COMMAND GRAMMAR (improves accuracy A LOT)

# 🔥 LOAD MODEL

model = Model(MODEL_PATH)
rec = KaldiRecognizer(model, 16000)

# 🔥 KEYWORDS FILTER

COMMAND_KEYWORDS = [
"open", "close", "download", "search",
"play", "stop", "list", "create", "delete"
]

# 🔥 CLEAN TEXT (fix "c h r o m e" issue)

def clean_text(text):
    words = text.split()
    if len(words) > 3 and all(len(w) == 1 for w in words):
        return "".join(words)
    return text

# 🔥 AUDIO CALLBACK

def callback(indata, frames, time, status):
    if status:
        print("⚠️", status)

    # FINAL RESULT
    if rec.AcceptWaveform(bytes(indata)):
        result = json.loads(rec.Result())
        text = result.get("text", "").strip()

        if text:
            text = clean_text(text)

            # FILTER COMMANDS
            if any(word in text for word in COMMAND_KEYWORDS):
                print("✅ Command:", text)
            else:
                print("❌ Ignored:", text)

print("🎤 Listening... Speak command (Ctrl+C to stop)")

# 🔥 START LISTENING

with sd.RawInputStream(
    samplerate=16000,
    blocksize=8000,
    dtype='int16',
    channels=1,
    callback=callback
):
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\n🛑 Stopped")
