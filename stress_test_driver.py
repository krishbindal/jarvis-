import os
import sys
import time
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from core.command_router import route_command
from executor.system_executor import execute_file_command
from skills import execute_skill
from utils.logger import get_logger

logger = get_logger("STRESS_TEST")

TEST_CASES = [
    # Phase 1: Multi-Step
    "open chrome and search best laptops under 1 lakh and then open first result",
    "open youtube and search lo-fi music and then play first video",
    "open google and search python tutorial and then scroll down",
    
    # Phase 2: Cross-App
    "open chrome and search instagram and then open it and then scroll for 5 seconds",
    "open whatsapp and send hi to Krish and then open instagram",
    "open chrome and search weather and extract temperature",
    
    # Phase 3: Context
    "open chrome",
    "search youtube",
    "open youtube and play a video",
    "pause it",
    
    # Phase 4: File System
    "open downloads folder and sort files by date",
    "create a folder named test123 in desktop and open it",
    "search for a pdf file in downloads and open it",
    
    # Phase 5: Download
    "download a youtube video and convert it to mp3",
    "search wallpaper and download first image",
    
    # Phase 6: NLU
    "i want to listen to music, do something",
    "i am bored, open something interesting",
    "talk to Krish and say i will call later",
    
    # Phase 7: Chained
    "open chrome and search python tutorial and open first video and play it",
    "open google and search best phones and open 2 results and compare them",
    
    # Phase 8: Error
    "open something that doesn't exist",
    "send message to unknown person"
]

def run_stress_test():
    report = []
    logger.info("="*50)
    logger.info("STARTING UNIVERSAL STRESS TEST")
    logger.info("="*50)

    for i, cmd in enumerate(TEST_CASES, 1):
        test_entry = {"id": i, "command": cmd, "status": "UNKNOWN", "steps": []}
        logger.input(cmd)
        
        try:
            start_time = time.time()
            routes = route_command(cmd)
            
            # Handle list for multi-step
            if not isinstance(routes, list):
                routes = [routes]
            
            for step in routes:
                action = step.get("action")
                target = step.get("target")
                stype = step.get("type")
                
                logger.action(f"{action} on {target} ({stype})")
                
                # Mock / Real Execution (we simulate success for the driver logic check)
                # In a real run, this would call system_executor or skills
                # Since we are "Hardened", we check if the route is valid.
                if action != "unknown" and action != "noop":
                    logger.execution(f"SUCCESS: Routed to {action}")
                    test_entry["steps"].append({"action": action, "success": True})
                else:
                    logger.error(f"FAILURE: Unrecognized intent for '{cmd}'")
                    test_entry["steps"].append({"action": action, "success": False})

            elapsed = time.time() - start_time
            test_entry["status"] = "PASSED" if all(s["success"] for s in test_entry["steps"]) else "FAILED"
            test_entry["time"] = elapsed
            
        except Exception as e:
            logger.error(f"CRASH: {str(e)}")
            test_entry["status"] = "CRASHED"
            test_entry["error"] = str(e)
            
        report.append(test_entry)
        logger.info(f"Test {i}/{len(TEST_CASES)}: {test_entry['status']}")
        logger.info("-" * 30)

    # Summary
    passed = len([r for r in report if r["status"] == "PASSED"])
    logger.info("="*50)
    logger.info(f"STRESS TEST COMPLETE: {passed}/{len(TEST_CASES)} PASSED")
    logger.info("="*50)
    
    with open("assets/logs/stress_test_report.json", "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    run_stress_test()
