# core/state.py
import operator
from typing import TypedDict, List, Annotated, Optional, Dict, Any
from langchain_core.messages import BaseMessage

class SkillGenerationData(TypedDict):
    """
    Specifically used to store temporary data during the 'skill generation' process.
    """
    skill_name: str           
    skill_description: str    
    file_name: str            # Added: Suggested filename
    generated_code: str       
    parameters: Dict[str, Any] # Added: Parameter Schema, must be passed to Updater
    error_message: Optional[str]
    node_id: Optional[str]     # v3: Track which node triggered this generation



from core.definitions import OrchestrationDAG

class AgentState(TypedDict):
    """
    Global state of the Agent.
    """
    # 1. Conversation history (supports appending)
    messages: Annotated[List[BaseMessage], operator.add]
    
    # 2. Original task input
    user_task: str
    
    # 3. List of currently loaded skills
    available_skills: List[Dict[str, str]]
    
    # 4. Mission DAG & Orchestration State
    dag: Optional[OrchestrationDAG]
    completed_nodes: Annotated[List[str], operator.add]
    node_outputs: Annotated[Dict[str, Any], operator.ior]
    validation_results: Annotated[Dict[str, bool], operator.ior]
    
    # v3 Orchestration State tracking
    current_node_id: Optional[str]
    state_gate: Optional[str]
    failed_nodes: Annotated[List[str], operator.add]
    error_history: Annotated[List[str], operator.add]
    
    # Legacy/Transition Fields (to be migrated or used selectively)
    route_action: str
    target_skill: Optional[str]
    skill_args: Optional[Dict[str, Any]]
    
    # 5. Skill generation sub-state
    skill_gen_data: Optional[SkillGenerationData]
    
    # 6. Final execution result
    final_result: Optional[str]
