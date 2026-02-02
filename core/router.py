# core/router.py
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.state import AgentState
from core.engine import get_llm
from skills.manager import SkillManager
from agents.prompts import ROUTER_SYSTEM_PROMPT, SUPERVISOR_SYSTEM_PROMPT
from core.definitions import OrchestrationDAG

def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor node: Classifies intent into reply, single tool, or complex mission.
    """
    print(f"\n--- [Supervisor] Classifying Intent: {state['user_task']} ---")
    
    skill_manager = SkillManager()
    skills_summary = skill_manager.get_skill_summaries()
    skills_text = json.dumps(skills_summary, ensure_ascii=False, indent=2)
    
    system_msg = SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT.format(skills_summary=skills_text))
    human_msg = HumanMessage(content=state['user_task'])
    
    llm = get_llm()
    response = llm.invoke([system_msg, human_msg])

    content = response.content.replace('```json', '').replace('```', '').strip()
    
    try:
        decision = json.loads(content)
        intent = decision.get("intent")
    except Exception as e:
        print(f"ERROR Parsing Supervisor Output: {e}")
        return {"route_action": "reply", "final_result": "System Error: Unable to classify intent."}

    print(f"--- [Supervisor] Intent: {intent} ({decision.get('reasoning')}) ---")

    if intent == "reply":
        return {
            "route_action": "reply",
            "final_result": decision.get("direct_reply", "I understand.")
        }
    elif intent == "execute_single":
        return {
            "route_action": "execute",
            "target_skill": decision.get("target_skill"),
            "skill_args": decision.get("target_skill_args", {}),
            "current_node_id": "single_task_node",
            "state_gate": None
        }
    else: # complex_mission
        return {"route_action": "decompose"}

def router_node(state: AgentState) -> AgentState:
    """
    Decomposer node (formerly router): Decomposes a complex mission into a DAG.
    """
    print(f"\n--- [Decomposer] Analyzing Mission: {state['user_task']} ---")
    
    skill_manager = SkillManager()
    skills_summary = skill_manager.get_skill_summaries()
    skills_text = json.dumps(skills_summary, ensure_ascii=False, indent=2)
    
    system_msg = SystemMessage(content=ROUTER_SYSTEM_PROMPT.format(skills_summary=skills_text))
    human_msg = HumanMessage(content=state['user_task'])
    
    llm = get_llm()
    response = llm.invoke([system_msg, human_msg])

    content = response.content.replace('```json', '').replace('```', '').strip()
    
    try:
        decision = json.loads(content)
        dag_data = decision.get("dag")
        if not dag_data:
            raise ValueError("No 'dag' field found in LLM response")
            
        dag = OrchestrationDAG(**dag_data)
    except Exception as e:
        print(f"ERROR Parsing Mission DAG: {e}\nContent: {content}")
        return {
            "route_action": "reply", 
            "final_result": "System Error: Unable to decompose mission into a valid DAG."
        }

    print(f"--- [Decomposer] Mission Decomposed into {len(dag.nodes)} nodes ---")

    return {
        "dag": dag,
        "completed_nodes": [],
        "node_outputs": {},
        "validation_results": {},
        "route_action": "orchestrate" 
    }