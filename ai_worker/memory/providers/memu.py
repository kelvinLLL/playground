import os
import tempfile
import asyncio
import logging
from typing import List, Dict, Optional, Any

from memu.app.service import MemoryService
from memu.app.settings import DatabaseConfig, MetadataStoreConfig, LLMConfig, LLMProfilesConfig

from ai_worker.memory.base import BaseMemoryProvider, MemoryItem, MemoryType

logger = logging.getLogger(__name__)

class MemUProvider(BaseMemoryProvider):
    """
    Memory provider using MemU (NevaMind-AI/memU).
    Requires Python 3.13+ and memu-py installed.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.service: Optional[MemoryService] = None
        self._temp_dir = tempfile.mkdtemp(prefix="memu_ingest_")
        
    async def initialize(self) -> None:
        try:
            # Load config from env or args
            api_key_chat = os.environ.get("OPENAI_API_KEY")
            base_url_chat = os.environ.get("OPENAI_BASE_URL")
            model_chat = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            
            api_key_embed = os.environ.get("OPENAI_API_KEY_EMBED")
            
            if not api_key_chat:
                logger.warning("OPENAI_API_KEY not found, MemU might fail.")
            
            db_config = DatabaseConfig(
                metadata_store=MetadataStoreConfig(
                    provider="inmemory"
                )
            )
            
            llm_profiles = LLMProfilesConfig(
                root={
                    "default": LLMConfig(
                        api_key=api_key_chat or "dummy",
                        base_url=base_url_chat,
                        chat_model=model_chat,
                        provider="openai"
                    ),
                    "embedding": LLMConfig(
                        api_key=api_key_embed or api_key_chat or "dummy",
                        embed_model="text-embedding-3-small",
                        provider="openai"
                    )
                }
            )
            
            self.service = MemoryService(
                database_config=db_config,
                llm_profiles=llm_profiles
            )
            logger.info("MemU service initialized (In-Memory)")
            
        except Exception as e:
            logger.error(f"Failed to initialize MemU: {e}")
            raise

    async def add(self, content: str, user_id: str, metadata: Optional[Dict] = None) -> str:
        if not self.service:
            await self.initialize()
            
        # MemU ingests resources (files). We must save content to a file.
        # Use content hash or UUID for filename to avoid collisions
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()
        file_path = os.path.join(self._temp_dir, f"{content_hash}.txt")
        
        with open(file_path, "w") as f:
            f.write(content)
            
        try:
            # MemU memorize workflow
            result = await self.service.memorize(
                resource_url=file_path,
                modality="text"
            )
            return str(result)  # resource_id
        except Exception as e:
            logger.error(f"MemU add failed: {e}")
            raise

    async def search(self, query: str, user_id: str, limit: int = 5) -> List[MemoryItem]:
        if not self.service:
            await self.initialize()
            
        try:
            # MemU retrieve workflow
            # Retrieve returns a structured context object
            context = await self.service.retrieve(
                queries=[{"role": "user", "content": query}]
            )
            
            # Convert MemU context to MemoryItems
            # Context is a dict (from our test output)
            # {'needs_retrieval': True, 'categories': [...], 'items': [...]}
            
            items = []
            
            # Extract items (facts)
            if "items" in context:
                for item in context["items"]:
                    # Item is a dict or object?
                    # Test output showed: {'id': ..., 'summary': ...} (Dict)
                    # MemU return type says dict[str, Any]
                    
                    content = item.get("summary", "")
                    m_type = item.get("memory_type", "fact")
                    score = item.get("score", 1.0)
                    
                    items.append(MemoryItem(
                        id=str(item.get("id")),
                        content=content,
                        user_id=user_id,
                        timestamp=0.0,
                        relevance=score,
                        memory_type=MemoryType.LONG_TERM,
                        metadata={"source": "memu_item", "type": m_type}
                    ))
            
            # Sort by relevance
            items.sort(key=lambda x: x.relevance, reverse=True)
            return items[:limit]
            
        except Exception as e:
            logger.error(f"MemU search failed: {e}")
            return []

    async def get_recent(self, user_id: str, limit: int = 10) -> List[MemoryItem]:
        # MemU doesn't have a direct "get recent" API easily accessible via Service
        # We might need to access the database directly or use a "wildcard" search
        return []

    async def delete(self, memory_id: str, user_id: str) -> bool:
        # MemU CRUD delete
        # Not fully exposed in Service top-level yet?
        return False

    async def reset(self, user_id: str) -> None:
        pass
