# core/orchestrator.py
import asyncio
from typing import List, Dict, Any, Optional
from core.state import AgentState
from core.definitions import DAGNode

def orchestrator_node(state: AgentState) -> AgentState:
    """
    Orchestrator node: Decides which nodes in the DAG can be executed next.
    Includes loop prevention by checking failed_nodes.
    """
    dag = state.get("dag")
    completed = state.get("completed_nodes", [])
    failed = state.get("failed_nodes", [])
    
    # If this was a single_task_node and it's done, we go to synthesis
    if "single_task_node" in completed:
        return {"route_action": "reply"}
    if "single_task_node" in failed:
        return {"route_action": "reply"}

    if not dag:
        # If no DAG but we reached here, it might be an issue with graph transitions
        return {"route_action": "end"}
    
    print(f"\n--- [Orchestrator] Progress: {len(completed)+len(failed)}/{len(dag.nodes)} nodes processed ---")
    
    # 1. Find nodes whose dependencies are all met
    executable_nodes = []
    for node in dag.nodes:
        if node.id in completed or node.id in failed:
            continue
        
        # Check if all dependencies are in the 'completed' list
        if all(dep in completed for dep in node.dependencies):
            # Also check if any dependency failed. If a dependency failed, this node should probably fail too or be skipped
            if any(dep in failed for dep in node.dependencies):
                 print(f"--- [Orchestrator] Skipping {node.id} because dependency failed ---")
                 # We'll mark it as failed (cascading failure)
                 return {"failed_nodes": [node.id]}
            
            executable_nodes.append(node)
    
    if not executable_nodes:
        # Check if all nodes are processed
        if len(completed) + len(failed) == len(dag.nodes):
            return {"route_action": "reply"} # Trigger synthesis
        else:
            print(f"--- [Orchestrator] DEADLOCK: Remaining nodes have unmet or failed dependencies ---")
            return {"route_action": "end", "final_result": "Mission aborted due to dependencies or failures."}
    
    # Select first executable node
    selected_node = executable_nodes[0]
    print(f"--- [Orchestrator] Next Task: {selected_node.id} ({selected_node.task}) ---")
    
    return {
        "route_action": selected_node.action_type,
        "target_skill": selected_node.target_skill,
        "skill_args": selected_node.target_skill_args,
        "current_node_id": selected_node.id,
        "state_gate": selected_node.state_gate
    }

def state_gate_validator(result: Any, gate_expression: Optional[str]) -> bool:
    """
    Validates the output of a node against its state gate.
    """
    if not gate_expression:
        return True
    
    try:
        context = {"result": result}
        return eval(gate_expression, {}, context)
    except Exception as e:
        print(f"State Gate Validation Error: {e}")
        return False
