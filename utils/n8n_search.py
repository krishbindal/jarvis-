import os
import json
import argparse
from pathlib import Path

def search_workflows(search_term, limit=10):
    """Searches through the Community_Library JSON files for a specific term."""
    base_dir = Path(__file__).parent.parent / "n8n_workflows" / "Community_Library"
    
    if not base_dir.exists():
        print(f"Directory not found: {base_dir}")
        return

    print(f"\n🔍 Searching for '{search_term}' in Community Library...")
    
    results = []
    
    try:
        # Walk through all categories
        for root, _, files in os.walk(base_dir):
            for file in files:
                if not file.endswith('.json'):
                    continue
                    
                path = Path(root) / file
                category = path.parent.name
                
                # Check filename match first
                if search_term.lower() in file.lower() or search_term.lower() in category.lower():
                    results.append({"path": path, "category": category, "name": file, "match_type": "name"})
                    continue
                    
                # Deeper scan inside JSON for node types
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'nodes' in data:
                            for node in data['nodes']:
                                if search_term.lower() in str(node.get('type', '')).lower() or \
                                   search_term.lower() in str(node.get('name', '')).lower():
                                    results.append({"path": path, "category": category, "name": file, "match_type": "node content"})
                                    break # found a match, move to next file
                except Exception:
                    pass
                
                if len(results) >= limit:
                    break
            
            if len(results) >= limit:
                break
                
    except Exception as e:
         print(f"Error while searching: {e}")
         
    if not results:
        print("❌ No matching workflows found.")
    else:
        print(f"✅ Found top {len(results)} matches:\n")
        for i, res in enumerate(results, 1):
            print(f"{i}. [{res['category']}] {res['name']} (Match: {res['match_type']})")
            print(f"   => {res['path'].relative_to(base_dir.parent)}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search n8n Community Workflows")
    parser.add_argument("query", type=str, help="Search term (e.g., 'discord', 'webhook', 'openai')")
    parser.add_argument("--limit", type=int, default=10, help="Max results to return")
    args = parser.parse_args()
    
    search_workflows(args.query, args.limit)
