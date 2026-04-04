import os
import difflib
from pathlib import Path

def find_app(target: str):
    target_lower = target.lower().strip()
    common_start = Path(os.environ.get('ALLUSERSPROFILE', 'C:\\ProgramData')) / 'Microsoft\\Windows\\Start Menu\\Programs'
    user_start = Path(os.environ.get('APPDATA', '')) / 'Microsoft\\Windows\\Start Menu\\Programs'
    app_paths = {}
    for start_dir in [common_start, user_start]:
        if start_dir.exists():
            for p in start_dir.rglob("*.lnk"):
                app_paths[p.stem.lower()] = str(p)
            for p in start_dir.rglob("*.exe"):
                app_paths[p.stem.lower()] = str(p)
                
    # Fuzzy match
    matches = difflib.get_close_matches(target_lower, app_paths.keys(), n=1, cutoff=0.5)
    
    # Also check substring match
    if not matches:
        for app_name in app_paths.keys():
            if target_lower in app_name or app_name in target_lower:
                matches.append(app_name)
                break 

    if matches:
        best_match = matches[0]
        app_path = app_paths[best_match]
        print(f"Found match: {best_match} at {app_path}")
        return app_path
    
    print(f"No match found for {target}")
    return None

if __name__ == "__main__":
    find_app("notepad")
    find_app("chrome")
    find_app("word")
