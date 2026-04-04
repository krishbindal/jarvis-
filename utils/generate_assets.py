import os
import base64

def generate_startup_sound():
    """Generates a placeholder startup.mp3 if it doesn't exist."""
    path = "assets/sounds/startup.mp3"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"[*] {path} already exists. Skipping.")
        return

    # A very short, valid MP3 (silence/blip) in base64 to avoid playback errors
    # This is a 1-second silent MP3 file
    silent_mp3_b64 = (
        "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGFtZTMuMTAwAqqqqqqqqqqqqqqqqqqqqv/7U"
        "RAAAAAAAAAAAAAAAAAAAAAAAAABYaW5nAAAADwAAAAAAAAAAAAYHBwcHBwcHBwcHBw"
        "cHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcH97VREAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAFBBSU5UAAAADwAAAExhbWUzLjEwMAqqqqqqqqqqqqqqqqqqqqv"
        "/7UVEAAAAAAAAAAAAAAAAAAAAAAAAAFBBSU5UAAAADwAAAExhbWUzLjEwMAqqqqqq"
        "qqqqqqqqqqqqqqqqv/7UREAAAAAAAAAAAAAAAAAAAAAAAAAFBBSU5UAAAADwAAAExh"
        "bWUzLjEwMAqqqqqqqqqqqqqqqqqqqq"
    )
    
    try:
        with open(path, "wb") as f:
            f.write(base64.b64decode(silent_mp3_b64))
        print(f"[+] Successfully generated placeholder: {path}")
    except Exception as e:
        print(f"[!] Failed to generate {path}: {e}")

if __name__ == "__main__":
    generate_startup_sound()
