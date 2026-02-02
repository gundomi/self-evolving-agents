# system_tools.py
import json
import os
import subprocess

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
            summary += f"- {s['name']}: {s['description']}\n"
            
        return summary
    except Exception as e:
        return {"error": f"Failed to read registry: {str(e)}"}

def run_shell_command(command: str):
    """
    Execute a shell command and return its output (stdout and stderr).
    Use this for system operations like git, ls, or checking service status.
    """
    print(f"--- [System Tool] Executing Shell Command: {command} ---")
    
    # v3: Auto-inject sudo if password is available
    from core.security import SecretManager
    secrets = SecretManager()
    sudo_pwd = secrets.get_password()
    
    try:
        if sudo_pwd and not command.strip().startswith("sudo"):
            # We use sudo -S -p '' to read password from stdin
            # This covers the case where the command needs privileges but user didn't type sudo
            # OR where the command IS 'sudo ...' handled below.
            # Actually, standardizing: wrap the command in sudo if it failed before? 
            # Or just blindly apply sudo if we have the password?
            # Safer: If we have the password, we assume the user intends to use it for this session.
            # We prepend sudo if not present.
            command = f"sudo -S -p '' {command}"
            input_data = f"{sudo_pwd}\n"
        else:
            input_data = None

        # Using shell=True for flexibility with pipes/redirects
        # If input_data is provided, we pass it to stdin
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            input=input_data,
            timeout=30 # Safety timeout
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
