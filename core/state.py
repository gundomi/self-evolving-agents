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



class AgentState(TypedDict):
    """
    Global state of the Agent.
    """
    # 1. Conversation history (supports appending)
    messages: Annotated[List[BaseMessage], operator.add]
    
    # 2. Original task input
    user_task: str
    
    # 3. List of currently loaded skills (summaries read from registry.json)
    # Format: [{"name": "...", "description": "..."}]
    available_skills: List[Dict[str, str]]
    
    # 4. Routing decision result
    # 'execute': Existing tool, execute directly
    # 'create': No tool, need to generate
    route_action: str
    
    # New: Target skill and arguments for execution
    target_skill: Optional[str]
    skill_args: Optional[Dict[str, Any]]
    
    # 5. Skill generation sub-state (if route_action == 'create')
    skill_gen_data: Optional[SkillGenerationData]
    
    # 6. Final execution result
    final_result: Optional[str]
