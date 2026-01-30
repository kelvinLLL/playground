# Plan: Memory System Implementation

## Objective
Implement a decoupled, pluggable Memory Architecture for the AI Worker, enabling seamless switching between Local JSON, MemU, and Mem0 backends.

## Work Items

- [ ] 1. **Architecture Documentation**
    - Create `ai_worker/docs/MEMORY_ARCHITECTURE.md` (content prepared).

- [ ] 2. **Core Interface (`ai_worker/memory/base.py`)**
    - Define `MemoryItem` dataclass.
    - Define `BaseMemoryProvider` abstract base class (ABC).
    - Define methods: `add`, `search`, `get_recent`, `delete`.

- [ ] 3. **Local Provider (`ai_worker/memory/providers/local_json.py`)**
    - Implement `LocalJSONProvider`.
    - Logic: Load/Save from `memory.json`.
    - Search: Simple keyword matching (fallback).

- [ ] 4. **Factory (`ai_worker/memory/factory.py`)**
    - Implement `MemoryFactory.create(provider_name: str, config: dict)`.
    - Support dynamic loading of providers.

- [ ] 5. **Verification**
    - Create `tests/test_memory.py` to verify the interface and LocalJSON behavior.

## Dependencies
- Standard library (`abc`, `typing`, `json`, `os`).
- No external DB required for Phase 1.
