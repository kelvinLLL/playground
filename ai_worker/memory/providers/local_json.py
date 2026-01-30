import json
import os
import time
import uuid
from typing import List, Dict, Optional, Any
from pathlib import Path

from ai_worker.memory.base import BaseMemoryProvider, MemoryItem, MemoryType

class LocalJSONProvider(BaseMemoryProvider):
    """
    A simple file-based memory provider for local development.
    Stores memories in a JSON file.
    """
    
    def __init__(self, file_path: str = "ai_worker_local_memory.json"):
        self.file_path = Path(file_path)
        self.memories: Dict[str, Dict] = {} # id -> raw_dict
        
    async def initialize(self) -> None:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.memories = json.load(f)
            except Exception as e:
                print(f"Error loading local memory: {e}")
                self.memories = {}
        else:
            self.memories = {}
            self._save()

    def _save(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, indent=2, ensure_ascii=False)

    async def add(self, content: str, user_id: str, metadata: Optional[Dict] = None) -> str:
        memory_id = str(uuid.uuid4())
        timestamp = time.time()
        
        item = {
            "id": memory_id,
            "content": content,
            "user_id": user_id,
            "timestamp": timestamp,
            "metadata": metadata or {},
            "memory_type": MemoryType.LONG_TERM.value
        }
        
        self.memories[memory_id] = item
        self._save()
        return memory_id

    async def search(self, query: str, user_id: str, limit: int = 5) -> List[MemoryItem]:
        # Simple keyword search (Not semantic!)
        results = []
        query_lower = query.lower()
        
        for mid, data in self.memories.items():
            if data["user_id"] != user_id:
                continue
                
            content = data["content"].lower()
            score = 0.0
            
            if query_lower in content:
                score = 1.0
            else:
                # Basic token overlap
                q_tokens = set(query_lower.split())
                c_tokens = set(content.split())
                overlap = len(q_tokens.intersection(c_tokens))
                if overlap > 0:
                    score = overlap / len(q_tokens)
            
            if score > 0:
                item = self._dict_to_item(data)
                item.relevance = score
                results.append(item)
                
        # Sort by relevance
        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:limit]

    async def get_recent(self, user_id: str, limit: int = 10) -> List[MemoryItem]:
        user_memories = [
            self._dict_to_item(m) 
            for m in self.memories.values() 
            if m["user_id"] == user_id
        ]
        user_memories.sort(key=lambda x: x.timestamp, reverse=True)
        return user_memories[:limit]

    async def delete(self, memory_id: str, user_id: str) -> bool:
        if memory_id in self.memories and self.memories[memory_id]["user_id"] == user_id:
            del self.memories[memory_id]
            self._save()
            return True
        return False

    async def reset(self, user_id: str) -> None:
        to_delete = [
            mid for mid, m in self.memories.items() 
            if m["user_id"] == user_id
        ]
        for mid in to_delete:
            del self.memories[mid]
        self._save()

    def _dict_to_item(self, data: Dict) -> MemoryItem:
        return MemoryItem(
            id=data["id"],
            content=data["content"],
            user_id=data["user_id"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
            memory_type=MemoryType(data.get("memory_type", "long_term"))
        )
