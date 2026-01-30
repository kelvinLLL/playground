"""
Base adapter class for platform-specific implementations.

All platform adapters (Discord, Feishu, etc.) inherit from this base class
and implement the required abstract methods.
"""

from abc import ABC, abstractmethod
import asyncio
import inspect
from typing import Any, Awaitable, Callable, Optional, Union

from ai_worker.core.message import StandardMessage, StandardResponse

# Type alias for message handlers (can be sync or async)
MessageHandler = Callable[[StandardMessage], Union[None, Awaitable[None]]]


class BaseAdapter(ABC):
    """
    Abstract base class for all platform adapters.

    Each adapter is responsible for:
    1. Connecting to the platform
    2. Receiving messages and converting to StandardMessage
    3. Sending responses by converting StandardResponse to platform format
    """

    def __init__(self, name: str):
        """
        Initialize the adapter.

        Args:
            name: Human-readable name for this adapter (e.g., "Discord", "Feishu")
        """
        self.name = name
        self._message_handler: Optional[MessageHandler] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if the adapter is currently running."""
        return self._running

    def set_message_handler(
        self, handler: MessageHandler
    ) -> None:
        """
        Set the callback function for handling incoming messages.

        Args:
            handler: Function (sync or async) that takes a StandardMessage and processes it
        """
        self._message_handler = handler

    @abstractmethod
    async def start(self) -> None:
        """
        Start the adapter and begin listening for messages.

        This method should:
        1. Connect to the platform
        2. Start the event loop for receiving messages
        3. Set self._running = True
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the adapter gracefully.

        This method should:
        1. Disconnect from the platform
        2. Clean up resources
        3. Set self._running = False
        """
        pass

    @abstractmethod
    async def send_message(
        self,
        channel_id: str,
        response: StandardResponse,
    ) -> bool:
        """
        Send a message to a specific channel.

        Args:
            channel_id: Platform-specific channel identifier
            response: StandardResponse to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def reply(
        self,
        original_message: StandardMessage,
        response: StandardResponse,
    ) -> Any:
        """
        Reply to a specific message.

        Args:
            original_message: The message to reply to
            response: StandardResponse to send as reply

        Returns:
            The sent message object/ID if successful, None otherwise
        """
        pass

    async def edit_message(
        self,
        message_handle: Any,
        new_content: str,
    ) -> bool:
        """
        Edit a previously sent message.
        
        Args:
            message_handle: The handle returned by reply() or send_message()
            new_content: New text content
            
        Returns:
            True if successful, False otherwise
        """
        # Default implementation does nothing (for backward compat)
        return False

    async def on_message(self, message: StandardMessage) -> None:
        """
        Handle an incoming message.

        This method is called by platform-specific event handlers
        after converting the message to StandardMessage format.

        Args:
            message: Standardized incoming message
        """
        if self._message_handler:
            result = self._message_handler(message)
            # Handle both sync and async handlers
            if asyncio.iscoroutine(result):
                await result

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return f"<{self.__class__.__name__}({self.name}) [{status}]>"
