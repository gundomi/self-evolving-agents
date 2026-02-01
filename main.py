# main.py
from langgraph.graph import StateGraph, END
from core.state import AgentState
from core.router import router_node
from core.creator import creator_node
from core.updater import updater_node

# --- Simulated Execution Node (Executor) ---
# In a real project, this would use Python REPL or tool_call to actually run the function
def executor_node(state: AgentState) -> AgentState:
    print(f"\n--- [Executor] Executing Skill... ---")
    # Simplified handling here: assume Router has confirmed the tool exists, just print it
    # Real scenario: find the function in sys.modules based on target_skill and run it
    return {"final_result": "Task executed successfully! (Simulated: called the newly generated tool)"}

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