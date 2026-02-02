# server.py
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os

from main import app as agent_app
from core.state import AgentState

api = FastAPI(title="Self-Evolving Agent API")

# Enable CORS for frontend development
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = []

class ChatResponse(BaseModel):
    response: str
    state: dict

@api.post("/chat")
async def chat(request: ChatRequest):
    """
    Handle chat requests by passing them to the LangGraph mission orchestrator.
    """
    try:
        inputs = {
            "user_task": request.message,
            "messages": [],
            "available_skills": [],
            "dag": None,
            "completed_nodes": [],
            "node_outputs": {},
            "validation_results": {},
            "route_action": "",
            "skill_gen_data": None
        }
        
        # Run the agent graph
        config = {"recursion_limit": 25} # Increased for complex missions
        
        final_state = None
        for output in agent_app.stream(inputs, config):
            for key, value in output.items():
                print(f"--- [Server] Node '{key}' completed ---")
                final_state = value
        
        if not final_state:
            raise HTTPException(status_code=500, detail="Agent failed to produce a response")

        # Extract final result (usually from the last 'reply' action or direct result)
        response_text = final_state.get("final_result", "Mission completed.")
        
        return {
            "response": response_text,
            "state": final_state
        }
        
    except Exception as e:
        print(f"--- [Server] Error: {str(e)} ---")
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files from frontend directory
if os.path.exists("frontend"):
    api.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000)
