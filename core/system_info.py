import os
import sys
import platform
import getpass
import psutil

def get_system_context():
    """
    Captures static system information for agent grounding.
    """
    try:
        context = {
            "os_name": os.name,
            "platform": platform.platform(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "python_version": sys.version.split()[0],
            "current_user": getpass.getuser(),
            "current_working_directory": os.getcwd(),
            "shell": os.environ.get("SHELL", "Unknown"),
            "cpu_count": os.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2)
        }
        
        # Security/Permission hint
        try:
            # Check if we have effective root (0)
            context["is_privileged"] = (os.geteuid() == 0)
        except AttributeError:
            context["is_privileged"] = False # Windows or other

        return context
    except Exception as e:
        return {"error": f"Failed to gather system context: {str(e)}"}
