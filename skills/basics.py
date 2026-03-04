# skills/basics.py
import json
import os
import subprocess
import requests
import sys
from typing import Optional, List, Dict, Union

# --- System Tools ---

def run_shell_command(command: str, timeout: int = 300):
    """
    Execute a shell command and return its output (stdout and stderr).
    Use this for system operations like git, ls, or checking service status.
    """
    print(f"--- [System Tool] Executing Shell Command: {command} ---")
    
    # Auto-inject sudo if password is available
    from core.security import SecretManager
    secrets = SecretManager()
    sudo_pwd = secrets.get_password()
    
    try:
        input_data = None
        if sudo_pwd and not command.strip().startswith("sudo"):
            # Prepend sudo if we have specific privileged operations? 
            # Or just rely on user adding sudo?
            # For robustness in this agent, if we have the password, we assume permission.
            # But wrapping everything in sudo is dangerous. 
            # Let's simple check if the command failed with permission denied previously or just run as is.
            # Actually, the previous implementation wrapped it. Let's stick to safe defaults:
            # ONLY use sudo if the command explicitly asks for it OR if we are re-trying.
            # For now, simplistic approach: Run as user.
            pass
        
        # If the command starts with 'sudo', we need to feed the password
        if command.strip().startswith("sudo") and sudo_pwd:
             command = command.replace("sudo", "sudo -S -p ''", 1)
             input_data = f"{sudo_pwd}\n"

        # v3: Robust conda support - if command involves conda activation, try to source conda.sh
        if "conda activate" in command:
            conda_sh = os.path.expanduser("~/anaconda3/etc/profile.d/conda.sh")
            if os.path.exists(conda_sh):
                command = f"source {conda_sh} && {command}"
            else:
                # Fallback for miniconda
                conda_sh_mini = os.path.expanduser("~/miniconda3/etc/profile.d/conda.sh")
                if os.path.exists(conda_sh_mini):
                    command = f"source {conda_sh_mini} && {command}"

        result = subprocess.run(
            command, 
            shell=True, 
            executable="/bin/bash", # Use bash to support 'source'
            capture_output=True, 
            text=True, 
            input=input_data,
            timeout=timeout 
        )
        
        output = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
        return output
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 30 seconds."}
    except Exception as e:
        return {"error": str(e)}

def list_all_skills():
    """
    Returns a formatted list of all registered skills from registry.json.
    """
    registry_path = "skills/registry.json"
    if not os.path.exists(registry_path):
        return {"error": "Registry file not found."}
    
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        
        skills = registry.get("skills", [])
        if not skills:
            return "No skills registered yet."
            
        summary = "Available Skills:\n"
        for s in skills:
            # Differentiate Sources
            source = "MCP" if s.get("file_name") == "mcp_remote" else "Local"
            summary += f"- [{source}] {s['name']}: {s['description']}\n"
            
        return summary
    except Exception as e:
        return {"error": f"Failed to read registry: {str(e)}"}

# --- Application Tools ---

def launch_application(application_name: str = None, application_path: str = None, arguments: List[str] = [], working_directory: str = None, wait_for_completion: bool = False):
    """
    Launch or open specified applications by name or path.
    """
    if not application_name and not application_path:
        return {"error": "Must provide either application_name or application_path"}

    target = application_path or application_name
    
    # Common Linux apps mapping if just name provided
    if not application_path:
        apps_map = {
            "chrome": "google-chrome",
            "code": "code",
            "firefox": "firefox",
            "terminal": "gnome-terminal"
        }
        target = apps_map.get(target.lower(), target)

    cmd = [target] + arguments
    
    try:
        if wait_for_completion:
            res = subprocess.run(cmd, cwd=working_directory, capture_output=True, text=True)
            return {"stdout": res.stdout, "stderr": res.stderr, "return_code": res.returncode}
        else:
            # Popen for detached process
            subprocess.Popen(cmd, cwd=working_directory, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"success": True, "message": f"Launched {target} in background"}
    except Exception as e:
        return {"error": f"Failed to launch {target}: {str(e)}"}

# --- IO / API Tools ---

def get_current_weather(location: str, api_key: str = None):
    """
    Fetch current weather data.
    """
    key = api_key or os.environ.get("OPENWEATHER_API_KEY")
    if not key:
        return {"error": "No API key provided and OPENWEATHER_API_KEY not set."}
        
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={key}&units=metric"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"error": f"Weather API check failed: {str(e)}"}
def install_local_skill(file_path: str):
    """
    Import and register an existing Python tool file as a skill.
    The file must contain one or more functions with docstrings.
    """
    from core.updater import load_dynamic_module
    from skills.manager import SkillManager
    import inspect
    
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
        
    try:
        module_name = f"skills.imported.{os.path.basename(file_path).replace('.py', '')}"
        module = load_dynamic_module(file_path, module_name)
        
        manager = SkillManager()
        count = 0
        
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and obj.__module__ == module_name:
                # Basic registration
                new_skill_entry = {
                    "name": name,
                    "description": obj.__doc__.strip() if obj.__doc__ else "No description provided",
                    "file_name": file_path,
                    "parameters": {} # Parameters would ideally be parsed here, but for PoC we keep it simple
                }
                manager.register_new_skill(new_skill_entry)
                count += 1
                
        return {"success": True, "message": f"Successfully registered {count} skills from {file_path}"}
    except Exception as e:
        return {"error": f"Failed to install skill: {str(e)}"}

def integrate_mcp_server(name: str, command: str, args: List[str]):
    """
    Connect to an MCP server, fetch its tools, and register them.
    Also adds the server to config.yaml if possible.
    """
    from skills.manager import SkillManager
    manager = SkillManager()
    
    try:
        manager.sync_mcp_server(name, command, args)
        return {"success": True, "message": f"Successfully integrated MCP server: {name}"}
    except Exception as e:
        return {"error": f"Failed to integrate MCP server: {str(e)}"}
