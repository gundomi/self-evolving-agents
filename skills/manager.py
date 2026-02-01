# skills/manager.py
import json
import os
from typing import List, Dict

class SkillManager:
    def __init__(self, registry_path: str = "skills/registry.json"):
        self.registry_path = registry_path
        self._ensure_registry()

    def _ensure_registry(self):
        """Ensure the registry file exists."""
        if not os.path.exists(self.registry_path):
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump({"skills": []}, f, ensure_ascii=False, indent=2)

    def load_registry(self) -> List[Dict]:
        """Load the complete registry."""
        with open(self.registry_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("skills", [])

    def get_skill_summaries(self) -> List[Dict[str, str]]:
        """
        Return only the lightweight summaries needed by the Router node
        (to reduce Token consumption, does not include detailed parameter Schema).
        """
        skills = self.load_registry()
        return [
            {"name": s["name"], "description": s["description"]} 
            for s in skills
        ]

    def register_new_skill(self, skill_data: Dict):
        """Register a newly generated skill."""
        skills = self.load_registry()
        # Simple duplicate check
        for s in skills:
            if s['name'] == skill_data['name']:
                # If it already exists, update it
                skills.remove(s)
                break
        
        skills.append(skill_data)
        
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump({"skills": skills}, f, ensure_ascii=False, indent=2)