"""
Tool Registry for dynamic tool management.

Allows tools to be registered via decorator and instantiated with configuration.
Supports automatic MCP-first tool resolution for seamless external integration.
"""

import logging
from typing import Dict, Type, Any, Optional, List

from ai_worker.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all available tools.
    
    Supports two tool sources:
    - Local tools: Registered via @register decorator
    - MCP tools: Registered dynamically at runtime via MCPClientManager
    
    MCP tools are namespaced as "{server}__{tool}" (e.g., "self_hosted__web_search").
    When creating a tool, MCP versions are automatically preferred over local versions.
    """
    
    _REGISTRY: Dict[str, Type[BaseTool]] = {}
    
    # Configuration: prefer MCP tools over local tools
    prefer_mcp: bool = True
    
    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a tool class.
        
        Args:
            name: Unique identifier for the tool
        """
        def decorator(tool_cls: Type[BaseTool]):
            if name in cls._REGISTRY:
                logger.warning(f"Tool '{name}' already registered. Overwriting.")
            
            cls._REGISTRY[name] = tool_cls
            return tool_cls
        return decorator
    
    @classmethod
    def get_tool_class(cls, name: str) -> Optional[Type[BaseTool]]:
        """Get a tool class by name."""
        return cls._REGISTRY.get(name)
    
    @classmethod
    def list_tools(cls) -> List[str]:
        """List all registered tool names."""
        return list(cls._REGISTRY.keys())
    
    @classmethod
    def list_local_tools(cls) -> List[str]:
        """List only local (non-MCP) tools."""
        return [name for name in cls._REGISTRY.keys() if "__" not in name]
    
    @classmethod
    def list_mcp_tools(cls) -> List[str]:
        """List only MCP tools (namespaced with __)."""
        return [name for name in cls._REGISTRY.keys() if "__" in name]
    
    @classmethod
    def find_mcp_version(cls, base_name: str) -> Optional[str]:
        """
        Find an MCP version of a tool by its base name.
        
        Args:
            base_name: The base tool name (e.g., "web_search")
            
        Returns:
            Full MCP tool name (e.g., "self_hosted__web_search") or None
        """
        # Look for any tool ending with __{base_name}
        for name in cls._REGISTRY.keys():
            if name.endswith(f"__{base_name}"):
                return name
        return None
    
    @classmethod
    def create_tool(cls, name: str, config: Optional[Dict[str, Any]] = None) -> BaseTool:
        """
        Instantiate a tool by name with configuration.
        
        If prefer_mcp is True and an MCP version exists, it will be used instead.
        This allows Workers to use ToolRegistry.create_tool("web_search") and
        automatically get the MCP version if available.
        
        Args:
            name: Tool name to create (e.g., "web_search")
            config: Configuration dictionary (e.g. settings) to extract parameters from
            
        Returns:
            Instantiated tool
            
        Raises:
            ValueError: If tool not found
        """
        resolved_name = name
        
        # If this is not already an MCP tool, try to find MCP version
        if cls.prefer_mcp and "__" not in name:
            mcp_name = cls.find_mcp_version(name)
            if mcp_name:
                logger.info(f"[MCP-First] Using '{mcp_name}' instead of local '{name}'")
                resolved_name = mcp_name
        
        tool_cls = cls.get_tool_class(resolved_name)
        if not tool_cls:
            raise ValueError(
                f"Tool '{name}' not found in registry. "
                f"Available: {cls.list_tools()}"
            )
        
        # MCP proxy tools don't need config injection
        if "__" in resolved_name:
            return tool_cls()
        
        # Local tools: apply config-based dependency injection
        if config:
            kwargs = {}
            if name in ["web_search", "game_guide"]:
                if "tavily_api_key" in config:
                    kwargs["tavily_api_key"] = config["tavily_api_key"]
            
            return tool_cls(**kwargs)
            
        return tool_cls()
