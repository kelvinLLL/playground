"""
Conversation memory for short-term context.

Manages per-user, per-channel conversation history with sliding window.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MemoryEntry:
    """A single memory entry."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Context for a single conversation thread."""

    messages: list[MemoryEntry] = field(default_factory=list)
    max_messages: int = 20
    max_age_seconds: int = 3600  # 1 hour

    def add(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """Add a message to the conversation."""
        entry = MemoryEntry(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(entry)
        self._cleanup()

    def _cleanup(self) -> None:
        """Remove old messages and enforce limits."""
        now = time.time()
        cutoff = now - self.max_age_seconds

        self.messages = [
            m for m in self.messages
            if m.timestamp > cutoff
        ][-self.max_messages:]

    def get_messages(self, limit: Optional[int] = None) -> list[dict[str, str]]:
        """Get messages in LLM-compatible format."""
        self._cleanup()
        messages = self.messages[-limit:] if limit else self.messages
        return [{"role": m.role, "content": m.content} for m in messages]

    def get_context_string(self, limit: int = 10) -> str:
        """Get conversation as a formatted string."""
        messages = self.get_messages(limit)
        lines = []
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()


class ConversationMemory:
    """
    Manages conversation memory across users and channels.

    Memory is keyed by (user_id, channel_id) to maintain separate
    conversation threads per user per channel.
    """

    def __init__(
        self,
        max_messages_per_conversation: int = 20,
        max_age_seconds: int = 3600,
    ):
        self.max_messages = max_messages_per_conversation
        self.max_age = max_age_seconds
        self._conversations: dict[tuple[str, str], ConversationContext] = defaultdict(
            lambda: ConversationContext(
                max_messages=self.max_messages,
                max_age_seconds=self.max_age,
            )
        )

    def _key(self, user_id: str, channel_id: str) -> tuple[str, str]:
        """Generate conversation key."""
        return (str(user_id), str(channel_id))

    def add_message(
        self,
        user_id: str,
        channel_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Add a message to a conversation."""
        key = self._key(user_id, channel_id)
        self._conversations[key].add(role, content, metadata)

    def add_user_message(
        self, user_id: str, channel_id: str, content: str
    ) -> None:
        """Add a user message."""
        self.add_message(user_id, channel_id, "user", content)

    def add_assistant_message(
        self, user_id: str, channel_id: str, content: str
    ) -> None:
        """Add an assistant message."""
        self.add_message(user_id, channel_id, "assistant", content)

    def get_conversation(
        self, user_id: str, channel_id: str, limit: Optional[int] = None
    ) -> list[dict[str, str]]:
        """Get conversation history."""
        key = self._key(user_id, channel_id)
        return self._conversations[key].get_messages(limit)

    def get_context_string(
        self, user_id: str, channel_id: str, limit: int = 10
    ) -> str:
        """Get conversation as formatted string."""
        key = self._key(user_id, channel_id)
        return self._conversations[key].get_context_string(limit)

    def clear_conversation(self, user_id: str, channel_id: str) -> None:
        """Clear a specific conversation."""
        key = self._key(user_id, channel_id)
        if key in self._conversations:
            self._conversations[key].clear()

    def clear_all(self) -> None:
        """Clear all conversations."""
        self._conversations.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        total_messages = sum(
            len(ctx.messages) for ctx in self._conversations.values()
        )
        return {
            "active_conversations": len(self._conversations),
            "total_messages": total_messages,
        }
