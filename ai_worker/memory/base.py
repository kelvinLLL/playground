from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

class MemoryType(Enum):
    SHORT_TERM = "short_term" # Conversation context
    LONG_TERM = "long_term"   # Facts, preferences, experiences
    EPISODIC = "episodic"     # Specific past events

@dataclass
class MemoryItem:
    id: str
    content: str
    user_id: str
    timestamp: float
    relevance: float = 1.0
    memory_type: MemoryType = MemoryType.LONG_TERM
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseMemoryProvider(ABC):
    """
    Abstract base class for memory providers.
    All memory backends (MemU, Mem0, LocalJSON) must implement this.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize connection to DB or load files."""
        pass

    @abstractmethod
    async def add(self, content: str, user_id: str, metadata: Optional[Dict] = None) -> str:
        """
        Add a memory item.
        
        Args:
            content: The text content to remember
            user_id: The user associated with this memory
            metadata: Optional metadata (source, tags, etc.)
            
        Returns:
            The memory_id of the created item
        """
        pass

    @abstractmethod
    async def search(self, query: str, user_id: str, limit: int = 5) -> List[MemoryItem]:
        """
        Search for relevant memories.
        
        Args:
            query: The search query
            user_id: User ID to filter by
            limit: Max results
            
        Returns:
            List of MemoryItems sorted by relevance
        """
        pass

    @abstractmethod
    async def get_recent(self, user_id: str, limit: int = 10) -> List[MemoryItem]:
        """Get most recently added memories."""
        pass
        
    @abstractmethod
    async def delete(self, memory_id: str, user_id: str) -> bool:
        """Delete a specific memory by ID."""
        pass
        
    @abstractmethod
    async def reset(self, user_id: str) -> None:
        """Clear all memories for a user."""
        pass
