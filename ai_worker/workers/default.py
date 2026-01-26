"""
Default Worker implementation.

A general-purpose AI assistant that handles general inquiries.
"""

import logging

from ai_worker.core.message import (
    MessageType,
    StandardMessage,
    StandardResponse,
)
from ai_worker.llm.base import BaseLLM, Message
from ai_worker.workers.base import BaseWorker, WorkerConfig

from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class DefaultWorker(BaseWorker):
    """
    The default AI employee.

    Handles general conversation, routing help, and non-specialized tasks.
    """

    def __init__(self, llm: BaseLLM):
        """
        Initialize the default worker.

        Args:
            llm: Language model instance
        """
        config = WorkerConfig(
            name="Assistant",
            description="A helpful general-purpose AI assistant.",
            system_prompt=(
                "You are a helpful AI employee assistant. "
                "Your goal is to assist users with their requests efficiently. "
                "You are part of a multi-agent system. "
                "If you cannot handle a request, suggest which specialist might be able to help "
                "(e.g., Quant Analyst for financial data, Strategy dev for coding)."
            ),
        )
        super().__init__(config)
        self.llm = llm

    async def process(
        self, 
        message: StandardMessage, 
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        """
        Process a general message using the LLM.

        Args:
            message: Incoming user message
            notifier: Progress callback

        Returns:
            Response message
        """
        try:
            # Build system prompt with user context if available
            system_content = self.system_prompt
            user_context = message.metadata.get("user_context", "") if message.metadata else ""
            if user_context:
                system_content += f"\n\nContext about this user:\n{user_context}"
            
            messages = [Message(role="system", content=system_content)]
            
            # Use conversation history from metadata (centralized memory)
            conversation_history = message.metadata.get("conversation_history", []) if message.metadata else []
            for msg in conversation_history[:-1]:  # Exclude current message (added below)
                messages.append(Message(role=msg["role"], content=msg["content"]))
            
            # Add current message
            messages.append(Message(role="user", content=message.content))

            # Get response from LLM
            llm_response = await self.llm.chat(messages)

            return StandardResponse(
                content=llm_response.content,
                message_type=MessageType.TEXT,
            )

        except Exception as e:
            logger.error(f"Error in DefaultWorker: {e}")
            return StandardResponse(
                content="I apologize, but I encountered an error processing your request.",
                message_type=MessageType.TEXT,
            )
