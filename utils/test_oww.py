import sounddevice as sd
import numpy as np
import openwakeword
from openwakeword.model import Model as OWWModel
import time

openwakeword.utils.download_models()
oww_model = OWWModel(wakeword_models=["hey_jarvis"], inference_framework="onnx")
print("Model loaded. Please clearly say 'Hey Jarvis'. Press Ctrl+C to stop.")

def cb(indata, frames, time_info, status):
    if status:
        print(f"Status: {status}")
    audio_array = np.frombuffer(bytes(indata), dtype=np.int16)
    try:
        prediction = oww_model.predict(audio_array)
        for model_name, score in prediction.items():
            if score > 0.3:  # Lower threshold for testing
                print(f"*** DETECTED: {model_name} (score: {score:.3f}) ***")
    except Exception as e:
        print(f"Error: {e}")

try:
    with sd.RawInputStream(
        samplerate=16000,
        blocksize=1280,
        dtype='int16',
        channels=1,
        callback=cb
    ):
        while True:
            time.sleep(1)
except KeyboardInterrupt:
    print("Stopped.")
