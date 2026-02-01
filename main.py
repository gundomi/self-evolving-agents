# main.py
from langgraph.graph import StateGraph, END
from core.state import AgentState
from core.router import router_node
from core.creator import creator_node
from core.updater import updater_node
from skills.manager import SkillManager
import os

# --- Real Execution Node (Executor) ---
def executor_node(state: AgentState) -> AgentState:
    skill_name = state.get("target_skill")
    args = state.get("skill_args") or {}
    
    print(f"\n--- [Executor] Executing Skill: {skill_name} with args: {args} ---")
    
    try:
        manager = SkillManager()
        skills = manager.load_registry()
        skill_metadata = next((s for s in skills if s["name"] == skill_name), None)
        
        if not skill_metadata:
            return {"final_result": f"Error: Skill '{skill_name}' not found in registry."}
            
        file_path = skill_metadata["file_name"]
        
        # Dynamically load the module
        from core.updater import load_dynamic_module
        module_name = f"skills.generated.{os.path.basename(file_path).replace('.py', '')}"
        module = load_dynamic_module(file_path, module_name)
        
        # Get the function
        func = getattr(module, skill_name)
        
        # Call the function
        result = func(**args)
        
        print(f"--- [Executor] Result: {result} ---")
        
        # Format result for user
        if isinstance(result, dict) and 'error' in result:
            return {"final_result": f"Tool Execution Error: {result['error']}"}
            
        return {"final_result": str(result)}
        
    except Exception as e:
        print(f"--- [Executor] Execution Failed: {str(e)} ---")
        return {"final_result": f"Execution Error: {str(e)}"}

# --- Build the Graph (Graph Construction) ---

workflow = StateGraph(AgentState)

# 1. Add nodes
workflow.add_node("router", router_node)
workflow.add_node("creator", creator_node)
workflow.add_node("updater", updater_node)
workflow.add_node("executor", executor_node)

# 2. Set entry point
workflow.set_entry_point("router")



def after_updater_decision(state: AgentState):
    # Check for errors
    gen_data = state.get("skill_gen_data")
    if gen_data and gen_data.get("error_message"):
        print(f"!!! Skill generation/update aborted: {gen_data.get('error_message')} !!!")
        return END # If error, end directly to avoid infinite loop
    
    # If route_action points to router (success), continue
    return "router"


# 3. Add conditional edges (Router decision)
def route_decision(state: AgentState):
    action = state.get("route_action")
    if action == "create":
        return "creator"
    elif action == "execute":
        return "executor"
    else: # reply
        return END

workflow.add_conditional_edges(
    "router",
    route_decision,
    {
        "creator": "creator",
        "executor": "executor",
        END: END
    }
)

# 4. Add normal edges (Loop logic)
workflow.add_edge("creator", "updater")

workflow.add_conditional_edges(
    "updater",
    after_updater_decision,
    {
        "router": "router",
        END: END
    }
)

workflow.add_edge("executor", END)

# 5. Compile
app = workflow.compile()

# --- Run Test ---
if __name__ == "__main__":
    print("=== Self-Evolving Agent Started ===")
    
    # Test case: Request a non-existent tool
    # Assume registry.json is empty initially
    user_input = "Help me generate a random password with length 12"
    
    inputs = {
        "user_task": user_input,
        "messages": [],
        "available_skills": [], # Will be reloaded inside Router
        "route_action": "",
        "skill_gen_data": None
    }
    
    # Run graph
    # recursion_limit prevents infinite loops
    for output in app.stream(inputs, {"recursion_limit": 10}):
        pass
        # Real-time streaming output is already printed in each node
    
    print("\n=== Final State ===")
    # output is the state of the last step
    print(output)