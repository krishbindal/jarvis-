import requests
import json
import time

URL = "http://localhost:5001"

def test_ping(message="Sir, your n8n automation is now fully operational."):
    payload = {
        "message": message,
        "type": "notification"
    }
    try:
        print(f"Sending notification to JARVIS: {message}")
        response = requests.post(URL, json=payload, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure JARVIS-X is running (python main.py) before running this test.")

if __name__ == "__main__":
    test_ping()
