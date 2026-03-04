import asyncio
import os
import shutil
from typing import Dict, List, Optional, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

class MCPClient:
    """
    Manages connections to MCP servers via stdio.
    """
    def __init__(self):
        self.servers = {} # {name: config}
        # In a real app, this config would be loaded from a settings file.
        # For now, we define some default servers if available.
        self._init_default_servers()
        self.exit_stack = AsyncExitStack()
        self.sessions = {} # {name: ClientSession}

    def _init_default_servers(self):
        # v3: Load servers from config.yaml
        from core.config_loader import settings
        mcp_servers = settings.get("mcp.servers", [])
        for server in mcp_servers:
            self.servers[server['name']] = {
                "command": server['command'],
                "args": server['args'],
                "env": server.get('env')
            }

    async def connect_to_server(self, name: str, command: str, args: List[str], env: Optional[Dict] = None):
        """
        Connect to a new MCP server.
        """
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        
        # We need to maintain the context manager lifecycle manually for a long-running app
        # This is complex in a stateless request model. 
        # Strategy: Connect-Listing-Disconnect for discovery. 
        # Connect-Execute-Disconnect for execution.
        # Ideally, we'd keep connections alive, but for v1 let's be stateless.
        pass

    async def list_tools(self, command: str, args: List[str]) -> List[Dict]:
        """
        Connects to a server, lists tools, and returns them formatted for our registry.
        """
        server_params = StdioServerParameters(command=command, args=args)
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                
                # Transform MCP tools to our internal format
                formatted_tools = []
                for tool in tools_result.tools:
                    formatted_tools.append({
                        "name": f"mcp__{tool.name}", # Namespace to avoid collision
                        "description": tool.description,
                        "file_name": "mcp_remote", # Marker
                        "parameters": tool.inputSchema,
                        "mcp_config": {
                            "command": command,
                            "args": args,
                            "original_name": tool.name
                        }
                    })
                return formatted_tools

    async def execute_tool(self, config: Dict, tool_name: str, arguments: Dict) -> Any:
        """
        Execute a tool on an MCP server.
        """
        command = config.get("command")
        args = config.get("args")
        original_name = config.get("original_name")
        
        server_params = StdioServerParameters(command=command, args=args)
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(original_name, arguments)
                return result

    # Helper for synchronous contexts (running in our sync executor for now, or via asyncio.run)
    def list_tools_sync(self, command: str, args: List[str]) -> List[Dict]:
        return asyncio.run(self.list_tools(command, args))

    def execute_tool_sync(self, config: Dict, tool_name: str, arguments: Dict) -> Any:
        return asyncio.run(self.execute_tool(config, tool_name, arguments))
