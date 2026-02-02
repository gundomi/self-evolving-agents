import json
import os
import time
import uuid
from typing import List, Dict, Optional

SESSION_FILE = "storage/sessions.json"

class SessionManager:
    def __init__(self):
        os.makedirs("storage", exist_ok=True)
        self.sessions = self._load_sessions()

    def _load_sessions(self) -> Dict:
        if not os.path.exists(SESSION_FILE):
            return {}
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_sessions(self):
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(self.sessions, f, indent=2)

    def create_session(self, title: str = "New Session") -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "id": session_id,
            "title": title,
            "created_at": time.time(),
            "updated_at": time.time(),
            "messages": [] # We will store chat history here for simple persistence
        }
        self._save_sessions()
        return session_id

    def list_sessions(self) -> List[Dict]:
        # Return sorted by updated_at desc
        s_list = list(self.sessions.values())
        s_list.sort(key=lambda x: x["updated_at"], reverse=True)
        return s_list

    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, title: Optional[str] = None, touch: bool = True):
        if session_id in self.sessions:
            if title:
                self.sessions[session_id]["title"] = title
            if touch:
                self.sessions[session_id]["updated_at"] = time.time()
            self._save_sessions()

    def add_message(self, session_id: str, role: str, content: str):
        if session_id in self.sessions:
            self.sessions[session_id]["messages"].append({
                "role": role,
                "content": content,
                "timestamp": time.time()
            })
            self._save_sessions()
