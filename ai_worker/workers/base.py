"""
Base worker class for AI employees.

Each worker represents a specialized AI employee with specific
roles, tools, and permissions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Callable

from ai_worker.core.message import StandardMessage, StandardResponse
from ai_worker.tools.base import BaseTool


@dataclass
class WorkerConfig:
    """Configuration for an AI worker."""

    name: str
    description: str
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)  # Tool names this worker can use
    permissions: dict[str, bool] = field(default_factory=dict)


class BaseWorker(ABC):
    """
    Abstract base class for all AI workers (employees).

    Each worker has:
    - A unique name/identity
    - A specific role/persona (defined by system prompt)
    - Access to specific tools
    - Defined permissions
    """

    def __init__(self, config: WorkerConfig):
        """
        Initialize the worker.

        Args:
            config: Worker configuration
        """
        self.config = config
        self.name = config.name
        self.description = config.description
        self._tools: dict[str, BaseTool] = {}
        self._memory: list[dict[str, Any]] = []  # Conversation memory

    @property
    def system_prompt(self) -> str:
        """Get the system prompt for this worker."""
        return self.config.system_prompt

    def register_tool(self, tool: BaseTool, as_name: Optional[str] = None) -> None:
        """
        Register a tool for this worker to use.

        Args:
            tool: Tool instance to register
            as_name: Override name to use as key (for MCP tools with namespaced names)
        """
        # Determine the key to use for registration
        key = as_name or tool.name
        
        # Check if this tool (or its base name) is in allowed tools
        base_name = tool.name.split("__")[-1] if "__" in tool.name else tool.name
        if base_name in self.config.tools or key in self.config.tools:
            self._tools[key] = tool

    def has_permission(self, permission: str) -> bool:
        """
        Check if this worker has a specific permission.

        Args:
            permission: Permission name to check

        Returns:
            True if worker has the permission, False otherwise
        """
        return self.config.permissions.get(permission, False)

    @abstractmethod
    async def process(
        self, 
        message: StandardMessage, 
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        """
        Process an incoming message and generate a response.

        Args:
            message: Incoming standardized message
            notifier: Optional async callback to send intermediate updates to user
                     Usage: await notifier("I'm thinking...")

        Returns:
            Response to send back
        """
        pass

    async def think(self, message: StandardMessage) -> str:
        """
        Generate a thought/reasoning process (for complex tasks).

        Override this method to implement chain-of-thought reasoning.

        Args:
            message: Incoming message to reason about

        Returns:
            Reasoning/thought process as string
        """
        return ""

    def add_to_memory(self, role: str, content: str) -> None:
        """
        Add a message to conversation memory.

        Args:
            role: Message role (user/assistant/system)
            content: Message content
        """
        self._memory.append({"role": role, "content": content})

    def clear_memory(self) -> None:
        """Clear conversation memory."""
        self._memory.clear()

    def get_memory(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        """
        Get conversation memory.

        Args:
            limit: Optional limit on number of messages to return

        Returns:
            List of memory entries
        """
        if limit:
            return self._memory[-limit:]
        return self._memory.copy()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.name})>"
