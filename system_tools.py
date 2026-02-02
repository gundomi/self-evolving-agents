# system_tools.py
import json
import os

def list_all_skills():
    """
    Returns a formatted list of all registered skills from registry.json.
    """
    registry_path = "skills/registry.json"
    if not os.path.exists(registry_path):
        return {"error": "Registry file not found."}
    
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        
        skills = registry.get("skills", [])
        if not skills:
            return "No skills registered yet."
            
        summary = "Available Skills:\n"
        for s in skills:
            summary += f"- {s['name']}: {s['description']}\n"
            
        return summary
    except Exception as e:
        return {"error": f"Failed to read registry: {str(e)}"}
