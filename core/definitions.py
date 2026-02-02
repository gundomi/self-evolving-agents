from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class SkillSchema(BaseModel):
    # ... existing SkillSchema ...
    name: str = Field(..., description="Name of the skill function")
    description: str = Field(..., description="Description of the skill")
    file_name: str = Field(..., description="Filename to save")
    parameters: Dict[str, Any] = Field(..., description="Parameter Schema")

class DAGNode(BaseModel):
    """
    Represents a single task in the execution graph.
    """
    id: str = Field(..., description="Unique identifier for the node")
    task: str = Field(..., description="Natural language description of the task")
    dependencies: List[str] = Field(default_factory=list, description="IDs of nodes that must complete before this one")
    action_type: str = Field(..., description="'execute' (use tool), 'create' (gen tool), or 'reply'")
    target_skill: Optional[str] = None
    target_skill_args: Optional[Dict[str, Any]] = None
    state_gate: Optional[str] = Field(None, description="Python-like expression to validate output (e.g., 'result > 0.95')")

class OrchestrationDAG(BaseModel):
    """
    A collection of nodes forming a Directed Acyclic Graph.
    """
    nodes: List[DAGNode]