# main.py
from langgraph.graph import StateGraph, END
from core.state import AgentState
from core.router import router_node, supervisor_node
from core.creator import creator_node
from core.updater import updater_node
from core.orchestrator import orchestrator_node, state_gate_validator
from skills.manager import SkillManager
import os

# --- Real Execution Node (Executor) ---
def executor_node(state: AgentState) -> AgentState:
    node_id = state.get("current_node_id")
    skill_name = state.get("target_skill")
    args = state.get("skill_args") or {}
    gate_expr = state.get("state_gate")
    
    print(f"\n--- [Executor] Node: {node_id} | Skill: {skill_name} | Args: {args} ---")
    
    try:
        manager = SkillManager()
        skills = manager.load_registry()
        skill_metadata = next((s for s in skills if s["name"] == skill_name), None)
        
        if not skill_metadata:
            print(f"--- [Executor] Error: Skill '{skill_name}' not found ---")
            return {"failed_nodes": [node_id], "error_history": [f"Skill '{skill_name}' not found"]}
            
        file_path = skill_metadata["file_name"]
        from core.updater import load_dynamic_module
        module_name = f"skills.generated.{os.path.basename(file_path).replace('.py', '')}"
        module = load_dynamic_module(file_path, module_name)
        
        func = getattr(module, skill_name)
        result = func(**args)
        
        print(f"--- [Executor] Raw Result: {result} ---")
        
        is_valid = state_gate_validator(result, gate_expr)
        print(f"--- [Executor] State Gate Validation: {'SUCCESS' if is_valid else 'FAILED'} ---")

        if not is_valid:
            return {"failed_nodes": [node_id], "error_history": [f"State gate validation failed for {node_id}"]}

        return {
            "completed_nodes": [node_id],
            "node_outputs": {node_id: result},
            "validation_results": {node_id: is_valid}
        }
        
    except Exception as e:
        print(f"--- [Executor] Execution Failed: {str(e)} ---")
        return {"failed_nodes": [node_id], "error_history": [f"Execution error in {node_id}: {str(e)}"]}

# --- Reply Node (Final Synthesis) ---
def reply_node(state: AgentState) -> AgentState:
    outputs = state.get("node_outputs", {})
    errors = state.get("error_history", [])
    
    if errors:
        result = f"Mission processed with some issues. Node Outputs: {outputs}. Errors: {errors}"
    elif outputs:
        result = f"Mission Accomplished. Node Outputs: {outputs}"
    else:
        result = state.get("final_result", "I understand.")
        
    return {"final_result": result}

# --- Build the Graph ---

workflow = StateGraph(AgentState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("decomposer", router_node)
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("creator", creator_node)
workflow.add_node("updater", updater_node)
workflow.add_node("executor", executor_node)
workflow.add_node("reply", reply_node)

workflow.set_entry_point("supervisor")

# Routing logic
def supervisor_decision(state: AgentState):
    action = state.get("route_action")
    if action == "decompose":
        return "decomposer"
    elif action == "execute":
        return "executor"
    else: # reply
        return "reply"

def orchestrator_decision(state: AgentState):
    action = state.get("route_action")
    if action == "execute":
        return "executor"
    elif action == "create":
        return "creator"
    elif action == "reply":
        return "reply"
    else: # end
        return END

workflow.add_conditional_edges("supervisor", supervisor_decision)
workflow.add_edge("decomposer", "orchestrator")
workflow.add_conditional_edges("orchestrator", orchestrator_decision)

workflow.add_edge("executor", "orchestrator")
workflow.add_edge("creator", "updater")
workflow.add_edge("updater", "orchestrator")
workflow.add_edge("reply", END)

app = workflow.compile()

if __name__ == "__main__":
    print("=== Sentinel-Architect v3 (Resilient) Started ===")
    user_input = "What can you do?"
    
    inputs = {
        "user_task": user_input,
        "messages": [],
        "available_skills": [],
        "dag": None,
        "completed_nodes": [],
        "failed_nodes": [],
        "node_outputs": {},
        "validation_results": {},
        "error_history": [],
        "route_action": "",
        "skill_gen_data": None
    }
    
    for output in app.stream(inputs, {"recursion_limit": 25}):
        pass
    
    print("\n=== Final Response ===")
    print(output)