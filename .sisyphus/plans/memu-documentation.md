# Plan: Document MemU Internals

## Objective
Create a comprehensive technical deep-dive into MemU based on local source code analysis. This will serve as the blueprint for implementing our own "MemU-Lite".

## Work Items
- [ ] 1. **Create `ai_worker/docs/MEMU_INTERNALS.md`**
    - **Architecture**: Diagram 3-Layer structure.
    - **Pipeline**: Document `ingest` -> `extract` -> `categorize` flow.
    - **Extraction Logic**: Detail the prompt engineering strategy (Profile vs Event) and XML parsing.
    - **Implementation Guide**: Concrete steps to emulate this using Python + SQLite + OpenAI.

## Verification
- File content reflects the specific findings from `memorize.py` and `prompts/`.
