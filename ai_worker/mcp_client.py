"""
MCP Client Manager.

Connects to external MCP servers and registers their tools into the local registry.
"""

import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ai_worker.tools.base import BaseTool, ToolResult
from ai_worker.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPProxyTool(BaseTool):
    """
    A proxy tool that delegates execution to a remote MCP server.
    """

    def __init__(
        self,
        session: ClientSession,
        local_name: str,
        remote_name: str,
        description: str,
        schema: dict
    ):
        """
        Args:
            session: MCP client session
            local_name: Namespaced name for local registry (e.g., "self_hosted__web_search")
            remote_name: Original tool name on remote server (e.g., "web_search")
            description: Tool description
            schema: JSON schema for parameters
        """
        super().__init__(name=local_name, description=description)
        self.session = session
        self.remote_name = remote_name
        self._schema = schema

    @property
    def parameters(self) -> dict[str, Any]:
        return self._schema

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            # Call remote tool using its ORIGINAL name
            result = await self.session.call_tool(self.remote_name, arguments=kwargs)
            
            # MCP returns a list of Content objects (TextContent, ImageContent, etc.)
            # We need to flatten this into a string for our BaseTool interface
            output_parts = []
            for content in result.content:
                if content.type == "text":
                    output_parts.append(content.text)
                elif content.type == "image":
                    output_parts.append(f"[Image: {content.mime_type}]")
                elif content.type == "resource":
                    output_parts.append(f"[Resource: {content.uri}]")
            
            full_output = "\n".join(output_parts)
            
            if result.isError:
                return ToolResult(success=False, data=None, error=full_output)
            
            return ToolResult(success=True, data=full_output)

        except Exception as e:
            return ToolResult(success=False, data=None, error=f"MCP Call Error: {str(e)}")


class MCPClientManager:
    """
    Manages connections to multiple MCP servers.
    """

    def __init__(self, config_path: Optional[str] = None):
        # Default to mcp_servers.json in the ai_worker package directory
        if config_path is None:
            package_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(package_dir, "mcp_servers.json")
        self.config_path = config_path
        self._exit_stack = AsyncExitStack()
        self._sessions: Dict[str, ClientSession] = {}

    async def start(self):
        """Read config and connect to all servers."""
        if not os.path.exists(self.config_path):
            logger.warning(f"MCP config file not found: {self.config_path}")
            return

        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return

        servers = config.get("mcpServers", {})
        logger.info(f"Found {len(servers)} MCP servers in config")

        for server_name, server_conf in servers.items():
            await self._connect_server(server_name, server_conf)

    async def _connect_server(self, name: str, config: dict):
        """Connect to a single MCP server."""
        try:
            command = config.get("command")
            args = config.get("args", [])
            env = config.get("env", {})
            
            # Merge current env with config env
            full_env = os.environ.copy()
            full_env.update(env)

            logger.info(f"Connecting to MCP server: {name} ({command} {' '.join(args)})")

            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=full_env
            )

            # Establish connection using AsyncExitStack to keep it open
            # 1. Connect stdio
            read, write = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            # 2. Start session
            session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            # 3. Initialize
            await session.initialize()
            self._sessions[name] = session
            
            # 4. List and register tools
            await self._register_remote_tools(name, session)
            
            logger.info(f"Connected to MCP server: {name}")

        except Exception as e:
            logger.error(f"Failed to connect to MCP server {name}: {e}")

    async def _register_remote_tools(self, server_name: str, session: ClientSession):
        """List tools from server and register them locally."""
        try:
            result = await session.list_tools()
            for tool in result.tools:
                # Namespace the tool name to avoid collisions
                # e.g., "self_hosted__web_search"
                local_name = f"{server_name}__{tool.name}"
                remote_name = tool.name
                
                logger.info(f"Discovered remote tool: {local_name} (Remote: {remote_name})")
                
                # Create Proxy Tool with both local and remote names
                proxy_tool = MCPProxyTool(
                    session=session,
                    local_name=local_name,
                    remote_name=remote_name,
                    description=f"[{server_name}] {tool.description}",
                    schema=tool.inputSchema
                )
                
                # Create a dynamic class that wraps this pre-made instance
                # This is needed because ToolRegistry.create_tool() calls cls()
                ToolClass = type(
                    f"MCPTool_{local_name}",
                    (BaseTool,),
                    {
                        "__init__": lambda self, **kw: None,
                        "execute": proxy_tool.execute,
                        "parameters": proxy_tool.parameters,
                        "name": proxy_tool.name,
                        "description": proxy_tool.description
                    }
                )
                
                # Register it
                ToolRegistry.register(local_name)(ToolClass)
                
        except Exception as e:
            logger.error(f"Failed to list tools for {server_name}: {e}")

    async def stop(self):
        """Close all connections."""
        await self._exit_stack.aclose()
