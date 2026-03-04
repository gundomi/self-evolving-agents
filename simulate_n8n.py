# simulate_n8n.py
import asyncio
import json
from main import app
from core.state import AgentState

async def run_sim():
    print("=== Simulating n8n Mission ===")
    inputs = {
        "user_task": "I want make a n8n workflow",
        "messages": [],
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
        "state_gate": None,
        "retry_count": 0,
        "strategic_analysis": None,
        "injected_instructions": None
    }
    
    # We will simulate node_1 failing state gate manually or just let it run if it really fails
    # But for a true test of the fix, we want to see it run.
    
    print("Invoking graph...")
    try:
        async for output in app.astream(inputs, {"recursion_limit": 100}):
            for node_name, state_update in output.items():
                print(f"\n>> Node: {node_name}")
                if "error_history" in state_update and state_update["error_history"]:
                    print(f"   Errors: {state_update['error_history']}")
                if "route_action" in state_update:
                    print(f"   Action: {state_update['route_action']}")
                if node_name == "repair":
                    print(f"   Strategic Analysis: {state_update.get('strategic_analysis')}")
    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_sim())
