"""
Base LLM class for language model integrations.

All LLM providers (OpenAI, Anthropic, etc.) inherit from this base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LLMResponse:
    """Response from an LLM."""

    content: str
    model: str
    usage: dict[str, int]  # token usage stats
    raw_response: Optional[Any] = None


@dataclass
class Message:
    """A single message in a conversation."""

    role: str  # system, user, assistant
    content: str


class BaseLLM(ABC):
    """
    Abstract base class for LLM integrations.

    Provides a unified interface for interacting with different
    language model providers.
    """

    def __init__(self, model: str):
        """
        Initialize the LLM client.

        Args:
            model: Model identifier (e.g., "gpt-4o", "claude-3-sonnet")
        """
        self.model = model

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send a chat completion request.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response

        Returns:
            LLM response
        """
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send a simple completion request.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            LLM response
        """
        pass

    async def chat_simple(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Simple chat interface - single user message, returns string.

        Args:
            user_message: User's message
            system_prompt: Optional system prompt

        Returns:
            Assistant's response as string
        """
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=user_message))

        response = await self.chat(messages)
        return response.content

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(model={self.model})>"
