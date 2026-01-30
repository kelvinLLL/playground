# Plan: Implement MemU Provider

## Objective
Integrate the MemU (memu-py) memory framework into our AI Worker via the `MemUProvider` class, enabling SOTA hierarchical memory.

## Prerequisites
- Python 3.13 environment (Verified: `ai_worker/.venv-313`).
- `memu-py` installed (Verified).

## Work Items

- [ ] 1. **Implement `ai_worker/memory/providers/memu.py`**
    - Class: `MemUProvider` (inherits `BaseMemoryProvider`).
    - Logic:
        - `initialize()`: Instantiate `memu.MemoryService`.
        - `add()`: Call `service.memorize()`.
        - `search()`: Call `service.retrieve()` and map output to `MemoryItem`.
        - `get_recent()`: Not directly supported by MemU, might need workaround (or search "*").

- [ ] 2. **Update `ai_worker/memory/factory.py`**
    - Add `memu` case to `create` method.
    - Import `MemUProvider` inside the conditional (to avoid import errors on non-3.13 envs).

- [ ] 3. **Verification**
    - Create `tests/test_memu_provider.py`.
    - Run using `.venv-313`.

## Dependencies
- `memu-py`
