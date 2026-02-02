# server.py
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os

from main import app as agent_app
from core.state import AgentState

api = FastAPI(title="Self-Evolving Agent API")

@api.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    if request.url.path.endswith((".js", ".css", ".html")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

# Enable CORS
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from core.sessions import SessionManager
from core.memory import VectorMemory

# Initialize Helpers
session_manager = SessionManager()
vector_memory = VectorMemory()

class CreateSessionRequest(BaseModel):
    title: str = "New Session"

@api.get("/sessions")
async def list_sessions():
    return session_manager.list_sessions()

@api.post("/sessions")
async def create_session(req: CreateSessionRequest):
    session_id = session_manager.create_session(req.title)
    return {"session_id": session_id, "title": req.title}

@api.get("/history/{session_id}")
async def get_history(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, message="Session not found")
    return session

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[List[dict]] = []

class AuthRequest(BaseModel):
    password: str

@api.post("/auth")
async def auth(request: AuthRequest):
    """
    Securely store provided sudo password.
    """
    from core.security import SecretManager
    SecretManager().set_password(request.password)
    return {"status": "success"}

@api.post("/chat")
async def chat(request: ChatRequest):
    """
    Handle chat requests using StreamingResponse for live updates via SSE.
    supports session persistence and RAG context.
    """
    # 1. Manage Session
    session_id = request.session_id
    if not session_id:
        # Create default or tmp session? 
        # For now, create a new one if missing
        session_id = session_manager.create_session(f"Chat {request.message[:20]}...")
    else:
        session_manager.update_session(session_id)
    
    # Save User message
    session_manager.add_message(session_id, "user", request.message)

    # Load History (to provide context to Agent)
    # The agent expects 'messages' list.
    session_data = session_manager.get_session(session_id)
    past_messages = session_data.get("messages", []) if session_data else []
    
    # Format for LangGraph (maybe limit to last N to save tokens?)
    # For now, we pass all (or rely on Memory RAG for efficient recall later)
    # Let's pass the last 10 messages for immediate context
    recent_history = past_messages[-10:] 

    async def event_generator():
        # Yield session ID first if it was created
        if not request.session_id:
            yield f"data: {json.dumps({'status': 'session_init', 'session_id': session_id})}\n\n"

        inputs = {
            "user_task": request.message,
            "messages": recent_history, # Populate history
            "available_skills": [],
            "dag": None,
            "completed_nodes": [],
            "failed_nodes": [],
            "node_outputs": {},
            "validation_results": {},
            "error_history": [],
            "route_action": "",
            "skill_gen_data": None,
            "current_node_id": None,
            "state_gate": None
        }
        
        config = {"recursion_limit": 50}
        final_response = ""
        final_dag = None

        try:
            # We use stream to get granular updates from LangGraph
            for output in agent_app.stream(inputs, config):
                for node_name, state_update in output.items():
                    route_action = state_update.get("route_action")
                    
                    # Capture DAG if available (from decomposer)
                    if state_update.get("dag"):
                        final_dag = state_update.get("dag")

                    # Handle Input Request (Sudo Auth)
                    if route_action == "ask_user":
                        payload = {
                            "node": node_name,
                            "status": "input_request", 
                            "update": {
                                "type": "password",
                                "message": "Permission Denied. Please enter sudo password to proceed."
                            }
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                        return 

                    # Format as SSE
                    payload = {
                        "node": node_name,
                        "status": "completed",
                        "update": {
                            "completed_nodes": state_update.get("completed_nodes"),
                            "current_node_id": state_update.get("current_node_id"),
                            "route_action": route_action,
                            "error": state_update.get("error_history")[-1] if state_update.get("error_history") else None
                        }
                    }
                    
                    # If it's the final synthesis result
                    if node_name == "reply":
                        final_response = state_update.get("final_result")
                        payload["response"] = final_response
                    
                    yield f"data: {json.dumps(payload)}\n\n"
                    await asyncio.sleep(0.1) # Small delay for smoother UI
            
            # End of stream logic
            if final_response:
                # Save Assistant response to Session
                session_manager.add_message(session_id, "system", final_response)
                
                # Save to Vector Memory (Topology & Result)
                # We embed the user intent + the resulting DAG structure + the outcome
                dag_json = final_dag.json() if final_dag else "{}"
                vector_memory.add_interaction(session_id, request.message, dag_json, final_response)

        except Exception as e:
            error_payload = {"status": "error", "message": str(e)}
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Serve static files
if os.path.exists("frontend"):
    api.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000)
