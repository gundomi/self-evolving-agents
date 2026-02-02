# core/updater.py
import os
import importlib.util
import sys
from core.state import AgentState
from skills.manager import SkillManager

def load_dynamic_module(file_path: str, module_name: str):
    """
    Dynamically load a Python module (Hot Reloading).
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    raise ImportError(f"Unable to load module from {file_path}")

def updater_node(state: AgentState) -> AgentState:
    """
    Updater node: Save code -> Register skill -> Hot reload -> Prepare for retry.
    """
    gen_data = state.get("skill_gen_data")
    if not gen_data or gen_data.get("error_message"):
        return {"route_action": "reply", "final_result": f"Skill generation failed: {gen_data.get('error_message')}"}

    skill_name = gen_data["skill_name"]
    file_name = gen_data["file_name"]
    code = gen_data["generated_code"]
    
    print(f"\n--- [Updater] Saving & Loading Skill: {skill_name} ---")

    save_dir = "skills/generated"
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, file_name)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception as e:
        return {"final_result": f"File write failed: {str(e)}"}

    try:
        manager = SkillManager()
        new_skill_entry = {
            "name": skill_name,
            "description": gen_data["skill_description"],
            "file_name": file_path,
            "parameters": gen_data["parameters"]
        }
        manager.register_new_skill(new_skill_entry)
    except Exception as e:
        return {"final_result": f"Registry update failed: {str(e)}"}

    try:
        module_name = f"skills.generated.{file_name.replace('.py', '')}"
        load_dynamic_module(file_path, module_name)
        print(f"--- [Updater] Successfully Loaded Module: {module_name} ---")
    except Exception as e:
        print(f"--- [Updater] Hot Reload Failed: {e} ---")
        return {"final_result": f"Newly generated code cannot be loaded: {str(e)}"}

    # v3 Closed loop: Return to orchestrator
    return {
        "skill_gen_data": None, 
        "route_action": "orchestrate" 
    }