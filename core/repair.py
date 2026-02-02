# core/repair.py
import json
import os
from langchain_core.messages import HumanMessage
from core.state import AgentState
from core.engine import get_llm
from agents.prompts import FIXER_SYSTEM_PROMPT
from skills.manager import SkillManager

def fixer_node(state: AgentState) -> AgentState:
    """
    Analyzes the most recent error and decides how to proceed.
    """
    errors = state.get("error_history", [])
    if not errors:
        return {"route_action": "orchestrate"}

    node_id = state.get("current_node_id")
    error_msg = errors[-1]
    node_output = state.get("node_outputs", {}).get(node_id, "No detailed output.")
    
    print(f"\n--- [Fixer] Analyzing Failure in Node: {node_id} ---")
    
    # 1. Prepare Skills Summary
    manager = SkillManager()
    skills_summary = manager.get_skill_summaries()
    
    # 2. Call LLM for diagnosis
    prompt = FIXER_SYSTEM_PROMPT.format(
        user_task=state.get("user_task"),
        node_id=node_id,
        error_message=error_msg,
        node_output=node_output,
        skills_summary=skills_summary
    )
    
    llm = get_llm(temperature=0)
    response = llm.invoke([HumanMessage(content=prompt)])
    
    try:
        decision = json.loads(response.content.replace('```json', '').replace('```', '').strip())
        print(f"--- [Fixer] Diagnosis: {decision.get('analysis')} ---")
        print(f"--- [Fixer] Strategy: {decision.get('strategy').upper()} ---")
        
        if decision.get("strategy") == "abort":
            return {"route_action": "reply", "final_result": f"Mission Aborted: {decision.get('analysis')}"}
            
        if "permission denied" in error_msg.lower():
            from core.security import SecretManager
            secrets = SecretManager()
            
            if secrets.has_password():
                print("--- [Fixer] SUDO: Password available. Retrying with sudo... ---")
                return {
                    "route_action": "orchestrate",
                    "error_history": ["Permission Denied. Retrying with sudo privileges."]
                }
            else:
                print("--- [Fixer] SUDO: Permission denied and no password. Requesting input... ---")
                return {
                    "route_action": "ask_user",
                    "error_history": ["Permission Denied. Requesting sudo password from user."]
                }
            
        elif decision.get("strategy") == "retrain":
            print("--- [Fixer] Strategy: RETRAIN. Preparing to patch skill code... ---")
            
            # 1. Identify the failed skill
            # We need to access state to find which skill failed
            # In executor_node, we set failed_nodes, but we don't strictly store the skill name in state globally
            # But the node definition in DAG has it.
            dag = state.get("dag")
            target_skill = None
            if dag:
                for node in dag.nodes:
                    if node.id == node_id:
                        target_skill = node.target_skill
                        break
            
            # Fallback if DAG is missing (single_task)
            if not target_skill:
                # supervisor set target_skill in state for single execution?
                # orchestrator sets 'target_skill' in updates, so it might be in state
                target_skill = state.get("target_skill")

            if not target_skill:
                return {"route_action": "reply", "final_result": "Fixer could not identify target skill for retrain."}

            # 2. Get current code
            manager = SkillManager()
            skills = manager.load_registry()
            skill_metadata = next((s for s in skills if s["name"] == target_skill), None)
            
            if not skill_metadata:
                 return {"route_action": "reply", "final_result": f"Skill {target_skill} not found in registry for patching."}

            try:
                with open(skill_metadata["file_name"], "r") as f:
                    current_code = f.read()
            except Exception as e:
                 return {"route_action": "reply", "final_result": f"Could not read source code: {e}"}

            # 3. Generate Fix
            from agents.prompts import SKILL_FIXER_PROMPT
            fix_prompt = SKILL_FIXER_PROMPT.format(
                skill_name=target_skill,
                current_code=current_code,
                file_name=os.path.basename(skill_metadata["file_name"]),
                error_message=error_msg
            )
            
            fix_response = llm.invoke([HumanMessage(content=fix_prompt)])
            
            try:
                fix_data = json.loads(fix_response.content.replace('```json', '').replace('```', '').strip())
                
                # 4. Route to Updater
                return {
                    "route_action": "update",
                    "skill_gen_data": {
                        "skill_name": fix_data["name"],
                        "skill_description": fix_data.get("description", "Patched by Fixer"),
                        "file_name": fix_data["file_name"],
                        "generated_code": fix_data["code"],
                        "parameters": fix_data["parameters"],
                        "node_id": node_id
                    }
                }
            except Exception as e:
                 print(f"--- [Fixer] Code generation failed: {e} ---")
                 return {"route_action": "reply", "final_result": f"Fixer failed to generate patch: {e}"}

        return {"route_action": "orchestrate"} # Default to retry/next node
        
    except Exception as e:
        print(f"--- [Fixer] Error parsing diagnosis: {e} ---")
        return {"route_action": "reply", "final_result": f"Fatal error during repair: {str(e)}"}
