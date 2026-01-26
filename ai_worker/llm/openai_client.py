"""
OpenAI LLM implementation.
"""

import logging
from typing import Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from ai_worker.config import OpenAIConfig
from ai_worker.llm.base import BaseLLM, LLMResponse, Message

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLM):
    """
    OpenAI API client wrapper.

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
            max_retries=5,  # Increase retries (default is 2)
            timeout=120.0   # Increase timeout
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
        # Convert internal Message objects to OpenAI dict format
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            response: ChatCompletion = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
            )

            message_content = response.choices[0].message.content or ""
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens
                if response.usage
                else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            return LLMResponse(
                content=message_content,
                model=response.model,
                usage=usage,
                raw_response=response,
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
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
