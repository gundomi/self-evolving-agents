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

    def save_registry(self, skills: List[Dict]):
        """Save the registry to disk."""
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump({"skills": skills}, f, ensure_ascii=False, indent=2)

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
        skills = [s for s in skills if s['name'] != skill_data['name']]
        
        skills.append(skill_data)
        self.save_registry(skills)

    def sync_mcp_server(self, server_name: str, command: str, args: List[str]):
        """
        Connect to an MCP server, fetch tools, and cache them in the registry.
        This allows the Supervisor to see them without runtime latency.
        """
        from core.mcp_client import MCPClient
        client = MCPClient()
        
        try:
            print(f"[SkillManager] Syncing MCP Server: {server_name}...")
            tools = client.list_tools_sync(command, args)
            
            if not tools:
                print(f"[SkillManager] No tools found in {server_name}.")
                return

            skills = self.load_registry()
            
            # Remove old tools from this server to avoid stale entries
            # We identify them by a special 'mcp_server_name' key we will inject
            skills = [s for s in skills if s.get('mcp_server_name') != server_name]

            # Inject server name metadata and add new ones
            for t in tools:
                t['mcp_server_name'] = server_name
                skills.append(t)
            
            self.save_registry(skills)
            print(f"[SkillManager] Successfully synced {len(tools)} tools from {server_name}.")
            
        except Exception as e:
            print(f"[SkillManager] Failed to sync MCP server {server_name}: {e}")