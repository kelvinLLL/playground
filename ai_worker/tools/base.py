"""
Base tool class for external integrations.

Tools extend the capabilities of AI workers, allowing them
to interact with external systems and APIs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    data: Any
    error: Optional[str] = None


class BaseTool(ABC):
    """
    Abstract base class for all tools.

    Tools provide specific capabilities to workers, such as:
    - Web search
    - Database queries
    - File operations
    - API calls
    """

    def __init__(self, name: str, description: str):
        """
        Initialize the tool.

        Args:
            name: Unique name for this tool
            description: Human-readable description of what this tool does
        """
        self.name = name
        self.description = description

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """
        Get the parameter schema for this tool.

        Returns:
            JSON Schema-like dict describing parameters
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with execution outcome
        """
        pass

    def to_function_schema(self) -> dict[str, Any]:
        """
        Convert tool to OpenAI function calling schema.

        Returns:
            Function schema dict for LLM function calling
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.name})>"
