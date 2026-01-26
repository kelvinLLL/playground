"""
StandardMessage - Unified message format across all platforms.

This module defines the standard message format that all adapters
convert to/from, enabling platform-agnostic message handling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class MessageType(Enum):
    """Types of messages supported by the system."""

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    CARD = "card"  # Interactive card (Feishu)
    COMMAND = "command"  # Slash command
    REACTION = "reaction"


class Platform(Enum):
    """Supported chat platforms."""

    DISCORD = "discord"
    FEISHU = "feishu"
    UNKNOWN = "unknown"


@dataclass
class User:
    """Standardized user representation."""

    id: str
    name: str
    display_name: Optional[str] = None
    is_bot: bool = False
    platform: Platform = Platform.UNKNOWN

    @property
    def mention(self) -> str:
        """Get mention string for this user."""
        return f"@{self.display_name or self.name}"


@dataclass
class Channel:
    """Standardized channel/conversation representation."""

    id: str
    name: str
    platform: Platform = Platform.UNKNOWN
    is_private: bool = False


@dataclass
class Attachment:
    """File or media attachment."""

    filename: str
    url: str
    content_type: Optional[str] = None
    size: Optional[int] = None


@dataclass
class StandardMessage:
    """
    Standardized message format for cross-platform compatibility.

    All platform-specific messages are converted to this format
    before being processed by the core system.
    """

    # Core fields
    id: str
    content: str
    message_type: MessageType = MessageType.TEXT

    # Source information
    platform: Platform = Platform.UNKNOWN
    author: Optional[User] = None
    channel: Optional[Channel] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: Optional[Any] = None  # Original platform message
    metadata: dict[str, Any] = field(default_factory=dict)  # Extensible metadata

    # Optional fields
    attachments: list[Attachment] = field(default_factory=list)
    mentions: list[User] = field(default_factory=list)
    reply_to: Optional[str] = None  # ID of message being replied to

    def has_mention(self, user_id: str) -> bool:
        """Check if this message mentions a specific user."""
        return any(u.id == user_id for u in self.mentions)

    def get_mentioned_names(self) -> list[str]:
        """Get list of mentioned user names (for @worker routing)."""
        return [u.name for u in self.mentions]

    def is_command(self, prefix: str = "!") -> bool:
        """Check if this message is a command."""
        return self.content.startswith(prefix)

    def get_command(self, prefix: str = "!") -> tuple[str, str]:
        """
        Parse command and arguments from message.

        Returns:
            Tuple of (command_name, arguments_string)
        """
        if not self.is_command(prefix):
            return "", self.content

        parts = self.content[len(prefix):].split(maxsplit=1)
        command = parts[0] if parts else ""
        args = parts[1] if len(parts) > 1 else ""
        return command, args


@dataclass
class StandardResponse:
    """
    Standardized response format for sending messages.

    Workers return this format, and adapters convert it
    to platform-specific message formats.
    """

    content: str
    message_type: MessageType = MessageType.TEXT

    # Optional fields
    attachments: list[Attachment] = field(default_factory=list)
    reply_to: Optional[str] = None  # Reply to specific message
    mentions: list[str] = field(default_factory=list)  # User IDs to mention

    # Platform-specific extras (e.g., embed for Discord, card for Feishu)
    extras: dict[str, Any] = field(default_factory=dict)
