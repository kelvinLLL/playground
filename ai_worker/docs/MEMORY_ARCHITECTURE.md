# AI Agent Memory Architecture Design

## 1. Philosophy: Decoupling & Pluggability

The goal is to provide a unified memory interface for the AI Worker, allowing the underlying memory backend to be swapped (MemU, Mem0, Zep, Chroma, Local JSON) without changing any business logic.

## 2. Core Abstractions

### 2.1 The Data Model (`MemoryItem`)
Standardized exchange format.

```python
@dataclass
class MemoryItem:
    id: str
    content: str              # The actual memory text
    user_id: str
    timestamp: float          # Unix timestamp
    relevance: float = 1.0    # For search results (0-1)
    metadata: Dict[str, Any] = field(default_factory=dict) # Source, type, etc.
```

### 2.2 The Interface (`BaseMemoryProvider`)
All providers MUST implement this contract.

```python
class BaseMemoryProvider(ABC):
    @abstractmethod
    async def add(self, content: str, user_id: str, metadata: Dict = None) -> str: ...
    
    @abstractmethod
    async def search(self, query: str, user_id: str, limit: int = 5) -> List[MemoryItem]: ...
    
    @abstractmethod
    async def get_recent(self, user_id: str, limit: int = 10) -> List[MemoryItem]: ...
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool: ...
```

## 3. Provider Strategy

We use a **Factory Pattern** to instantiate providers based on configuration.

### Supported Providers (Planned)

1.  **`LocalJSONProvider` (Default/Dev)**
    *   **Backend**: Simple `memory.json` file.
    *   **Search**: Basic keyword match or brute-force cosine sim (if numpy available).
    *   **Pros**: Zero dependencies, fully local, easy to debug.
    *   **Cons**: Not scalable, no semantic search (unless augmented).

2.  **`MemUProvider` (SOTA)**
    *   **Backend**: MemU Framework.
    *   **Features**: Graph + Vector hybrid, hierarchical storage.
    *   **Integration**: Wraps `memu-py` calls.

3.  **`Mem0Provider` (Alternative)**
    *   **Backend**: Mem0 API / Local.
    *   **Integration**: Wraps `mem0ai` SDK.

## 4. Integration Point

The `DefaultWorker` (and other workers) will hold a `memory` instance.

```python
# In Worker Initialization
self.memory = MemoryFactory.create(settings.memory.provider)

# In Process Loop
# 1. Recall
relevant_memories = await self.memory.search(user_message, user_id)
context_str = format_memories(relevant_memories)

# 2. Inject Context
system_prompt += f"\n\nRecall:\n{context_str}"

# 3. Memorize (Post-process or via Tool)
# The LLM can decide to "save" something explicitly via a tool,
# OR we can auto-save summaries.
await self.memory.add(summary, user_id)
```

## 5. Directory Structure

```
ai_worker/
  └── memory/
      ├── __init__.py       # Exports BaseMemoryProvider, MemoryFactory
      ├── base.py           # Abstract Base Classes & Data Models
      ├── factory.py        # Logic to load providers
      └── providers/
          ├── __init__.py
          ├── local_json.py # Reference implementation
          ├── memu.py       # MemU adapter
          └── mem0.py       # Mem0 adapter
```
