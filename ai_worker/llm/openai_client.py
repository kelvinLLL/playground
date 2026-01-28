"""
OpenAI LLM implementation with Function Calling support.
"""

import json
import logging
from typing import Any, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from ai_worker.config import OpenAIConfig
from ai_worker.llm.base import BaseLLM, LLMResponse, Message, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLM):
    """
    OpenAI API client wrapper with function calling support.

    Handles communication with OpenAI's API (GPT-4o, etc).
    """

    def __init__(self, config: OpenAIConfig):
        """
        Initialize OpenAI client.

        Args:
            config: OpenAI configuration
        """
        super().__init__(config.model)
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            max_retries=5,
            timeout=120.0
        )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert internal Message objects to OpenAI dict format."""
        openai_messages = []
        for m in messages:
            msg: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            if m.name:
                msg["name"] = m.name
            openai_messages.append(msg)
        return openai_messages

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert internal ToolDefinition to OpenAI format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in tools
        ]

    def _parse_response(self, response: ChatCompletion) -> LLMResponse:
        """Parse OpenAI response into LLMResponse."""
        message = response.choices[0].message
        content = message.content or ""
        
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args
                ))
        
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }
        
        return LLMResponse(
            content=content,
            model=response.model,
            usage=usage,
            raw_response=response,
            tool_calls=tool_calls,
            finish_reason=response.choices[0].finish_reason or "stop"
        )

    async def chat(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send a chat completion request to OpenAI.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            LLM response
        """
        openai_messages = self._convert_messages(messages)

        try:
            response: ChatCompletion = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
            )
            return self._parse_response(response)

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def chat_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tool_choice: str = "auto",
    ) -> LLMResponse:
        """
        Send a chat request with function calling / tools.

        Args:
            messages: List of conversation messages
            tools: List of tool definitions
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            tool_choice: "auto", "none", or "required"

        Returns:
            LLM response with potential tool_calls
        """
        openai_messages = self._convert_messages(messages)
        openai_tools = self._convert_tools(tools)

        try:
            response: ChatCompletion = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                tools=openai_tools,
                tool_choice=tool_choice,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
            )
            return self._parse_response(response)

        except Exception as e:
            logger.error(f"OpenAI API error (with tools): {e}")
            raise

    async def complete(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send a simple completion request (wrapped as chat).

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            LLM response
        """
        messages = [Message(role="user", content=prompt)]
        return await self.chat(messages, temperature, max_tokens)
