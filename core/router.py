# core/router.py
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.state import AgentState
from core.engine import get_llm
from skills.manager import SkillManager
from agents.prompts import ROUTER_SYSTEM_PROMPT

def router_node(state: AgentState) -> AgentState:
    """
    Router node: Decides whether to execute an existing tool or generate a new one.
    """
    print(f"\n--- [Router] Analyzing Task: {state['user_task']} ---")
    
    # 1. Get existing skill summaries
    skill_manager = SkillManager()
    skills_summary = skill_manager.get_skill_summaries()
    skills_text = json.dumps(skills_summary, ensure_ascii=False, indent=2)
    
    # 2. Construct Prompt
    system_msg = SystemMessage(content=ROUTER_SYSTEM_PROMPT.format(skills_summary=skills_text))
    human_msg = HumanMessage(content=state['user_task'])
    
    # 3. Call LLM
    llm = get_llm()
    response = llm.invoke([system_msg, human_msg])

    content = response.content.replace('```json', '').replace('```', '').strip()
    # 4. Parse result
    try:
        decision = json.loads(content)
    except Exception as e:
        print(f"ERROR Parsing Router Output: {e}")
        # Downgrade strategy: Default reply
        return {**state, "route_action": "reply", "final_result": "System Error: Unable to parse routing decision."}

    action = decision.get("action")
    print(f"--- [Router] Decision: {action.upper()} ---")

    # 5. Update state
    updates = {}
    
    if action == "execute":
        updates["route_action"] = "execute"
        updates["target_skill"] = decision.get("target_skill")
        updates["skill_args"] = decision.get("target_skill_args", {})
        print(f"--- [Router] Target Skill: {updates['target_skill']} with args: {updates['skill_args']} ---")
        
    elif action == "create":
        updates["route_action"] = "create"
        # Initialize generation data
        updates["skill_gen_data"] = {
            "skill_name": "", # Generate later
            "skill_description": decision.get("missing_skill_desc", "General tool"),
            "generated_code": "",
            "file_path": "",
            "error_message": None
        }
        updates["target_skill"] = None
        updates["skill_args"] = None
        
    elif action == "reply":
        updates["route_action"] = "reply"
        updates["final_result"] = decision.get("reply_content", "I understand.")
        updates["target_skill"] = None
        updates["skill_args"] = None
    
    # Note: LangGraph's State update uses merge logic; only return changed fields.
    return updates