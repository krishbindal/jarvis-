import asyncio
import edge_tts
import pygame
import tempfile
import os
import sys

VOICE = "en-GB-RyanNeural"

async def test_tts():
    print("--- JARVIS-X Voice Diagnostic ---")
    text = "System check complete. Sir, can you hear my voice clearly?"
    
    try:
        print(f"1. Initializing Pygame Mixer...")
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        pygame.mixer.init()
        print(f"   Status: {pygame.mixer.get_init()}")
        
        print(f"2. Synthesizing test audio with edge-tts...")
        communicate = edge_tts.Communicate(text, VOICE)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name
        await communicate.save(tmp_path)
        print(f"   Audio saved to: {tmp_path}")
        
        print(f"3. Playing audio...")
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        print(f"4. Cleaning up...")
        pygame.mixer.music.unload()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        print("\nDIAGNOSTIC COMPLETE.")
        print("If you heard the voice, the issue is likely with the main app loop or permissions.")
        print("If you did NOT hear anything, check your default Windows playback device.")
        
    except Exception as e:
        print(f"\n[ERROR] Diagnostic failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_tts())
