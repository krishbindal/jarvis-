import logging
import time
from core.app import JarvisApp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_router():
    app = JarvisApp(auto_start=True)
    
    apps_to_test = ["notepad", "word"]
    
    for app_name in apps_to_test:
        print(f"--- TESTING open {app_name} ---")
        app._handle_command({"text": f"open {app_name}", "source": "voice"})
        
if __name__ == "__main__":
    test_router()
