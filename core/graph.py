from langgraph.graph import StateGraph, END
from core.state import AgentState

def create_graph(config):
    workflow = StateGraph(AgentState)
    
    # Define Nodes
    # workflow.add_node("router", router_node)
    # workflow.add_node("creator", creator_node)
    
    # Define Edges
    # workflow.set_entry_point("router")
    
    return workflow.compile()
