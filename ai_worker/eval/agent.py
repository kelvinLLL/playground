from typing import List, Optional, Dict, Any
import logging
from ai_worker.memory.base import BaseMemoryProvider, MemoryItem
from ai_worker.memory.factory import MemoryFactory

logger = logging.getLogger(__name__)


class MemAgent:
    """
    A simplified agent for memory evaluation.
    Wraps a memory provider and exposes a clean interface for benchmarks.
    """

    def __init__(self, provider_name: str = "local"):
        self.provider_name = provider_name
        self.provider: Optional[BaseMemoryProvider] = None

    async def initialize(self) -> None:
        """Must be called before use to initialize the underlying provider."""
        if not self.provider:
            logger.info(f"Initializing MemAgent with provider: {self.provider_name}")
            self.provider = await MemoryFactory.create(self.provider_name)

    async def add_memory(
        self, content: str, user_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a memory item."""
        if not self.provider:
            await self.initialize()

        # Ensure provider is not None (for type checking)
        assert self.provider is not None
        return await self.provider.add(content, user_id, metadata)

    async def search(
        self, query: str, user_id: str, limit: int = 5
    ) -> List[MemoryItem]:
        """Search for relevant memories."""
        if not self.provider:
            await self.initialize()

        assert self.provider is not None
        return await self.provider.search(query, user_id, limit)

    async def reset(self, user_id: str) -> None:
        """Clear all memories for a user."""
        if not self.provider:
            await self.initialize()

        assert self.provider is not None
        await self.provider.reset(user_id)
