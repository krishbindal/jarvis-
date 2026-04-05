import os
import google.generativeai as genai
from config import GEMINI_API_KEY

def list_models():
    if not GEMINI_API_KEY:
        print("No GEMINI_API_KEY found.")
        return
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("Listing models...")
    try:
        # Use simple iteration
        for model in client.models.list():
            print(f"Model: {model.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models()
